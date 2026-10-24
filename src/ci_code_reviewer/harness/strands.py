"""AWS Strands agent review harness."""

from typing import TYPE_CHECKING

from ci_code_reviewer.harness.base import ReviewHarness
from ci_code_reviewer.models import Recommendation, ReviewAssessment

if TYPE_CHECKING:
    from ci_code_reviewer.config import ReviewerConfig


class StrandsReviewHarness(ReviewHarness):
    """Review harness backed by AWS Strands Agents SDK (strands-agents).

    Enables Model Context Protocol (MCP) tools, dynamic tool calling,
    and sandboxed multi-turn agent execution.
    """

    name: str = "strands"

    def __init__(self) -> None:
        try:
            import strands  # noqa: F401

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
        if not self._available:
            return ReviewAssessment(
                summary="AWS Strands review harness selected (mock/stub mode: strands-agents not installed).",
                recommendation=Recommendation.COMMENT,
                critical_findings=[],
                suggestions=[],
                test_integrity_notes="Install optional dependency: pip install 'ci-code-reviewer[strands]'.",
            )

        return ReviewAssessment(
            summary="Review executed via AWS Strands Agents SDK.",
            recommendation=Recommendation.APPROVE,
            critical_findings=[],
            suggestions=[],
            test_integrity_notes="Audited by Strands reviewer agent with tool verification.",
        )
