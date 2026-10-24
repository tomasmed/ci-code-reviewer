"""GitHub REST API integration client for pull request review automation."""

import os
from typing import Any

import httpx

from ci_code_reviewer.config import VotingConfig
from ci_code_reviewer.models import (
    Recommendation,
    ReviewAssessment,
    ReviewComment,
)


def resolve_review_event(recommendation: Recommendation, voting: VotingConfig) -> str:
    """Determine the GitHub review event string (APPROVE, REQUEST_CHANGES, or COMMENT).

    If code-owner voting is disabled, always returns 'COMMENT' for safe advisory mode.
    """
    if not voting.enabled:
        return "COMMENT"

    if recommendation == Recommendation.APPROVE:
        return "APPROVE" if voting.allow_approve else "COMMENT"
    elif recommendation == Recommendation.REQUEST_CHANGES:
        return "REQUEST_CHANGES" if voting.allow_request_changes else "COMMENT"

    return "COMMENT"


def format_review_body(
    assessment: ReviewAssessment,
    blast_radius_context: str = "",
    unanchored_comments: list[ReviewComment] | None = None,
) -> str:
    """Construct markdown body for top-level pull request review."""
    badge_map = {
        Recommendation.APPROVE: "✅ Approved",
        Recommendation.REQUEST_CHANGES: "❌ Changes Requested",
        Recommendation.COMMENT: "💬 Advisory Feedback",
    }
    verdict_badge = badge_map.get(assessment.recommendation, assessment.recommendation.value)

    sections = [
        "## 🤖 CI Code Review Assessment",
        f"**Recommendation Verdict:** {verdict_badge}\n",
        f"{assessment.summary}\n",
    ]

    if assessment.lens_summaries:
        sections.append("### 🔍 Review Lens Evaluations")
        for lens_name, summary in sorted(assessment.lens_summaries.items()):
            sections.append(f"- **`{lens_name}`**: {summary}")
        sections.append("")

    if assessment.test_integrity_notes:
        sections.append("### 🧪 QA & Test Integrity")
        sections.append(f"{assessment.test_integrity_notes}\n")

    if blast_radius_context:
        sections.append(blast_radius_context)
        sections.append("")

    all_unanchored = list(unanchored_comments or [])
    if all_unanchored:
        sections.append("### ⚠️ Unanchored Findings & Out-of-Diff Observations")
        sections.append(
            "_The following findings were detected across files or lines that could not be anchored inline:_\n"
        )
        for finding in all_unanchored:
            lens_tag = f"`{finding.lens}`" if finding.lens else "general"
            loc = (
                f"`{finding.file_path}:{finding.line_number}`"
                if finding.line_number
                else f"`{finding.file_path}`"
            )
            sections.append(
                f"- **[{finding.severity.upper()}]** {loc} (Lens: {lens_tag}): **{finding.title}**\n  {finding.body}"
            )
        sections.append("")

    return "\n".join(sections).strip()


class GitHubClient:
    """Client for GitHub REST API interacting with pull requests and reviews."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.base_url = base_url.rstrip("/")

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ci-code-reviewer/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            transport=transport,
            timeout=30.0,
        )

    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch raw unified git diff for a pull request."""
        url = f"/repos/{repo}/pulls/{pr_number}"
        response = self._client.get(
            url,
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        response.raise_for_status()
        return response.text

    def get_pr_info(self, repo: str, pr_number: int) -> dict[str, Any]:
        """Fetch pull request metadata."""
        url = f"/repos/{repo}/pulls/{pr_number}"
        response = self._client.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            "head_sha": data["head"]["sha"],
            "base_ref": data["base"]["ref"],
            "title": data.get("title", ""),
            "author": data.get("user", {}).get("login", ""),
        }

    def post_review(
        self,
        repo: str,
        pr_number: int,
        commit_sha: str,
        assessment: ReviewAssessment,
        voting: VotingConfig | None = None,
        blast_radius_context: str = "",
    ) -> dict[str, Any]:
        """Publish structured ReviewAssessment to GitHub PR.

        Includes automatic 422 fallback recovery if inline comment line numbers
        fall outside diff hunks.
        """
        voting_cfg = voting or VotingConfig()
        event = resolve_review_event(assessment.recommendation, voting_cfg)

        all_findings = assessment.critical_findings + assessment.suggestions
        comments: list[dict[str, Any]] = []

        for f in all_findings:
            if f.line_number is not None and f.file_path:
                lens_prefix = f"[Lens: {f.lens}] " if f.lens else ""
                severity_badge = f"[{f.severity.upper()}] "
                body = f"**{lens_prefix}{severity_badge}{f.title}**\n\n{f.body}"
                comments.append(
                    {
                        "path": f.file_path,
                        "line": f.line_number,
                        "side": f.side,
                        "body": body,
                    }
                )

        initial_body = format_review_body(
            assessment=assessment,
            blast_radius_context=blast_radius_context,
            unanchored_comments=[],
        )

        payload: dict[str, Any] = {
            "commit_id": commit_sha,
            "body": initial_body,
            "event": event,
            "comments": comments,
        }

        url = f"/repos/{repo}/pulls/{pr_number}/reviews"
        response = self._client.post(url, json=payload)

        # Handle 422 Unprocessable Entity (e.g., line outside diff hunk)
        if response.status_code == 422 and comments:
            fallback_body = format_review_body(
                assessment=assessment,
                blast_radius_context=blast_radius_context,
                unanchored_comments=all_findings,
            )
            fallback_payload: dict[str, Any] = {
                "commit_id": commit_sha,
                "body": fallback_body,
                "event": event,
                "comments": [],
            }
            fallback_response = self._client.post(url, json=fallback_payload)
            fallback_response.raise_for_status()
            return fallback_response.json()

        response.raise_for_status()
        return response.json()
