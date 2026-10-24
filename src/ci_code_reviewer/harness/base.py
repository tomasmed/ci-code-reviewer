"""Abstract base class for review harnesses."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ci_code_reviewer.models import ReviewAssessment

if TYPE_CHECKING:
    from ci_code_reviewer.config import ReviewerConfig


class ReviewHarness(ABC):
    """Abstract interface that all agent review backends must implement."""

    name: str = "base"

    @abstractmethod
    def review(
        self,
        diff: str,
        context: str,
        config: "ReviewerConfig",
    ) -> ReviewAssessment:
        """Execute a review on the provided diff and context.

        Args:
            diff: The raw unified git diff string.
            context: In-repo contextual information (ADRs, AGENTS.md, rules).
            config: The active ReviewerConfig instance.

        Returns:
            A structured ReviewAssessment model.
        """
        pass
