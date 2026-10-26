"""Native review harness evaluating diffs through specialized sub-agent lens turns."""

import json
import logging
from typing import TYPE_CHECKING

import litellm

from ci_code_reviewer.harness.base import ReviewHarness
from ci_code_reviewer.lenses import (
    ReviewLensConfig,
    diff_matches_lens,
    extract_touched_files,
    load_lens_context,
)
from ci_code_reviewer.models import (
    LensTurnResult,
    Recommendation,
    ReviewAssessment,
    ReviewComment,
)

if TYPE_CHECKING:
    from ci_code_reviewer.config import ReviewerConfig

logger = logging.getLogger(__name__)


class NativeReviewHarness(ReviewHarness):
    """Ultra-fast review harness evaluating diffs through specialized sub-agent lens turns."""

    name: str = "native"

    def review(
        self,
        diff: str,
        context: str,
        config: "ReviewerConfig",
    ) -> ReviewAssessment:
        touched_files = extract_touched_files(diff)
        active_lenses = [lens for lens in config.lenses if diff_matches_lens(lens, touched_files)]

        if not active_lenses:
            active_lenses = [lens for lens in config.lenses if lens.enabled]

        all_critical_findings: list[ReviewComment] = []
        all_suggestions: list[ReviewComment] = []
        lens_summaries: dict[str, str] = {}
        has_blocker = False

        for lens in active_lenses:
            lens_result = self._execute_lens_turn(lens, diff, context, config)
            lens_summaries[lens.name] = lens_result.summary

            for comment in lens_result.findings:
                comment.lens = lens.name
                if comment.severity == "blocker":
                    all_critical_findings.append(comment)
                    if lens.blocking:
                        has_blocker = True
                else:
                    all_suggestions.append(comment)

        fallback_lenses = [
            lens.name
            for lens in active_lenses
            if "offline/fallback mode" in lens_summaries.get(lens.name, "")
        ]
        all_lenses_fell_back = bool(active_lenses) and len(fallback_lenses) == len(active_lenses)

        if has_blocker:
            rec = Recommendation.REQUEST_CHANGES
        elif all_suggestions:
            rec = Recommendation.COMMENT
        elif all_lenses_fell_back:
            # Open stance / fail-open: All lenses hit provider/connection errors.
            # Avoid emitting a misleading formal approval when zero active inspection occurred.
            rec = Recommendation.COMMENT
        else:
            rec = Recommendation.APPROVE

        if all_lenses_fell_back:
            summary_text = (
                f"Evaluated diff across {len(active_lenses)} review lenses: "
                + ", ".join(f"[{lens.name}]" for lens in active_lenses)
                + ". Notice: All lenses operated in open-stance fallback mode due to upstream provider/model error. Active LLM inspection was bypassed."
            )
        else:
            summary_text = (
                f"Evaluated diff across {len(active_lenses)} review lenses: "
                + ", ".join(f"[{lens.name}]" for lens in active_lenses)
                + f". Found {len(all_critical_findings)} blockers and {len(all_suggestions)} suggestions."
            )
            if fallback_lenses:
                summary_text += (
                    f" (Note: {len(fallback_lenses)} lens(es) operated in fallback mode)."
                )

        test_notes = lens_summaries.get(
            "test_integrity", "Test integrity evaluated by review lens."
        )

        return ReviewAssessment(
            summary=summary_text,
            recommendation=rec,
            critical_findings=all_critical_findings,
            suggestions=all_suggestions,
            test_integrity_notes=test_notes,
            lens_summaries=lens_summaries,
        )

    def _execute_lens_turn(
        self,
        lens: ReviewLensConfig,
        diff: str,
        global_context: str,
        config: "ReviewerConfig",
    ) -> LensTurnResult:
        lens_context = load_lens_context(lens)
        combined_context = f"{global_context}\n\n{lens_context}".strip()

        turn_prompt = f"""Review the following Git Diff exclusively through the '{lens.name}' lens.

--- LENS MISSION & SPECIFICATIONS ---
{lens.prompt}

--- IN-REPO CONTEXT ---
{combined_context}

--- GIT DIFF ---
{diff}

Respond strictly in valid JSON adhering to this schema:
{{
  "summary": "Brief summary of findings for this lens",
  "findings": [
    {{
      "file_path": "path/to/file",
      "line_number": 123,
      "side": "RIGHT",
      "severity": "blocker" | "suggestion" | "note",
      "title": "Short issue title",
      "body": "Detailed explanation and suggested fix"
    }}
  ]
}}
"""
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a specialized code review sub-agent evaluating the '{lens.name}' lens. "
                    "Maintain zero noise, avoid stylistic or formatting commentary, and focus exclusively on your mission."
                ),
            },
            {"role": "user", "content": turn_prompt},
        ]

        try:
            response = litellm.completion(
                model=config.model,
                messages=messages,
                response_format={"type": "json_object"},
                api_base=config.auth.api_base,
            )
            raw_content = response.choices[0].message.content
            data = json.loads(raw_content)
            findings: list[ReviewComment] = []
            for item in data.get("findings", []):
                comment = ReviewComment.model_validate(item)
                comment.lens = lens.name
                findings.append(comment)

            return LensTurnResult(
                lens_name=lens.name,
                summary=data.get("summary", f"Completed {lens.name} turn."),
                findings=findings,
                has_blockers=any(f.severity == "blocker" for f in findings),
            )
        except Exception as e:
            logger.error(
                "Review lens '%s' turn execution failed: %s",
                lens.name,
                e,
                exc_info=True,
            )
            return LensTurnResult(
                lens_name=lens.name,
                summary=(
                    f"Sub-agent turn for lens '{lens.name}' encountered an error "
                    "and could not complete review. Check CI logs for details (offline/fallback mode)."
                ),
                findings=[],
                has_blockers=False,
            )
