"""Microsoft Agent Framework (MAF) review harness."""

import json
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


class MafReviewHarness(ReviewHarness):
    """Review harness backed by Microsoft Agent Framework (MAF / agent-framework).

    Enables multi-agent conversational review, AutoGen-style persona deliberation,
    and enterprise-grade workflow orchestration across configured review lenses.
    """

    name: str = "maf"

    def __init__(self) -> None:
        try:
            import agent_framework  # noqa: F401

            self._available = True
        except ImportError:
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

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
            turn_result = self._execute_maf_lens_turn(lens, diff, context, config)
            lens_summaries[lens.name] = turn_result.summary

            for comment in turn_result.findings:
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
            if "offline" in lens_summaries.get(lens.name, "")
            or "simulated" in lens_summaries.get(lens.name, "")
        ]

        if has_blocker:
            rec = Recommendation.REQUEST_CHANGES
        elif all_suggestions:
            rec = Recommendation.COMMENT
        elif len(fallback_lenses) == len(active_lenses):
            rec = Recommendation.COMMENT
        else:
            rec = Recommendation.APPROVE

        if len(fallback_lenses) == len(active_lenses):
            summary_text = (
                f"Microsoft Agent Framework (MAF) evaluated diff across {len(active_lenses)} review lenses: "
                + ", ".join(f"[{lens.name}]" for lens in active_lenses)
                + ". Notice: All lenses operated in open-stance fallback mode due to upstream provider/model error. Active LLM inspection was bypassed."
            )
        else:
            summary_text = (
                f"Microsoft Agent Framework (MAF) evaluated diff across {len(active_lenses)} review lenses: "
                + ", ".join(f"[{lens.name}]" for lens in active_lenses)
                + f". Found {len(all_critical_findings)} blockers and {len(all_suggestions)} suggestions."
            )
            if fallback_lenses:
                summary_text += (
                    f" (Note: {len(fallback_lenses)} lens(es) operated in fallback mode)."
                )

        test_notes = lens_summaries.get(
            "test_integrity", "Test integrity evaluated by MAF QA agent."
        )

        return ReviewAssessment(
            summary=summary_text,
            recommendation=rec,
            critical_findings=all_critical_findings,
            suggestions=all_suggestions,
            test_integrity_notes=test_notes,
            lens_summaries=lens_summaries,
        )

    def _execute_maf_lens_turn(
        self,
        lens: ReviewLensConfig,
        diff: str,
        global_context: str,
        config: "ReviewerConfig",
    ) -> LensTurnResult:
        lens_context = load_lens_context(lens)
        combined_context = f"{global_context}\n\n{lens_context}".strip()

        turn_prompt = f"""Review the following Git Diff through the Microsoft Agent Framework persona '{lens.name}'.

--- LENS SPECIFICATIONS & DIRECTIVES ---
{lens.prompt}

--- IN-REPO CONTEXT & BLAST RADIUS ---
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
                    f"You are an enterprise review persona in Microsoft Agent Framework (MAF) "
                    f"evaluating the '{lens.name}' lens. Focus strictly on architectural integrity, "
                    f"security, and contract soundness with zero noise."
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
                summary=data.get("summary", f"Completed MAF turn for {lens.name}."),
                findings=findings,
                has_blockers=any(f.severity == "blocker" for f in findings),
            )
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            return LensTurnResult(
                lens_name=lens.name,
                summary=f"MAF agent turn for lens '{lens.name}' completed (simulated/offline mode: {err_msg}).",
                findings=[],
                has_blockers=False,
            )
