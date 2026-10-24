"""Factory for selecting and instantiating review harnesses."""

from ci_code_reviewer.harness.base import ReviewHarness
from ci_code_reviewer.harness.maf import MafReviewHarness
from ci_code_reviewer.harness.native import NativeReviewHarness
from ci_code_reviewer.harness.strands import StrandsReviewHarness

HARNESS_REGISTRY: dict[str, type[ReviewHarness]] = {
    "native": NativeReviewHarness,
    "strands": StrandsReviewHarness,
    "maf": MafReviewHarness,
}


def get_harness(name: str) -> ReviewHarness:
    """Retrieve an instantiated review harness by name.

    Supported harnesses:
    - 'native': Ultra-fast LiteLLM direct structured review.
    - 'strands': AWS Strands Agents SDK with MCP tools.
    - 'maf': Microsoft Agent Framework (MAF).

    Raises:
        ValueError: If harness name is unrecognized.
    """
    normalized = name.strip().lower()
    harness_cls = HARNESS_REGISTRY.get(normalized)
    if not harness_cls:
        valid_options = ", ".join(f"'{k}'" for k in HARNESS_REGISTRY.keys())
        raise ValueError(f"Unknown harness '{name}'. Supported harnesses are: {valid_options}")
    return harness_cls()
