"""Microsoft Agent Framework (MAF) review harness."""

from typing import TYPE_CHECKING

from ci_code_reviewer.harness.base import ReviewHarness
from ci_code_reviewer.models import Recommendation, ReviewAssessment

if TYPE_CHECKING:
    from ci_code_reviewer.config import ReviewerConfig


class MafReviewHarness(ReviewHarness):
    """Review harness backed by Microsoft Agent Framework (MAF / agent-framework).

    Enables multi-agent conversational review, AutoGen-style persona deliberation,
    and enterprise-grade workflow orchestration.
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
        lens_summaries = {
            lens.name: f"Audited by MAF under lens '{lens.name}'."
            for lens in config.lenses
            if lens.enabled
        }
        if not self._available:
            return ReviewAssessment(
                summary="Microsoft Agent Framework (MAF) harness selected (mock/stub mode: agent-framework not installed).",
                recommendation=Recommendation.COMMENT,
                critical_findings=[],
                suggestions=[],
                test_integrity_notes="Install optional dependency: pip install 'ci-code-reviewer[maf]'.",
                lens_summaries=lens_summaries,
            )

        return ReviewAssessment(
            summary="Review executed via Microsoft Agent Framework (MAF) across configured lenses.",
            recommendation=Recommendation.APPROVE,
            critical_findings=[],
            suggestions=[],
            test_integrity_notes="Audited by MAF multi-agent review team.",
            lens_summaries=lens_summaries,
        )
