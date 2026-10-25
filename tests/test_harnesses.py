"""Tests for review harnesses and factory."""

import pytest

from ci_code_reviewer.config import ReviewerConfig
from ci_code_reviewer.harness.factory import HARNESS_REGISTRY, get_harness
from ci_code_reviewer.harness.maf import MafReviewHarness
from ci_code_reviewer.harness.native import NativeReviewHarness
from ci_code_reviewer.harness.strands import StrandsReviewHarness
from ci_code_reviewer.models import Recommendation


def test_harness_registry_contains_launch_targets() -> None:
    assert "native" in HARNESS_REGISTRY
    assert "strands" in HARNESS_REGISTRY
    assert "maf" in HARNESS_REGISTRY


def test_get_harness_factory() -> None:
    native = get_harness("native")
    assert isinstance(native, NativeReviewHarness)
    assert native.name == "native"

    strands = get_harness("strands")
    assert isinstance(strands, StrandsReviewHarness)
    assert strands.name == "strands"

    maf = get_harness("maf")
    assert isinstance(maf, MafReviewHarness)
    assert maf.name == "maf"


def test_get_harness_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown harness 'nonexistent'"):
        get_harness("nonexistent")


def test_native_fallback_review() -> None:
    harness = NativeReviewHarness()
    config = ReviewerConfig(harness="native")
    result = harness.review(
        diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new",
        context="Repo context",
        config=config,
    )
    assert result.recommendation == Recommendation.COMMENT
    assert "open-stance fallback mode" in result.summary
    assert len(result.lens_summaries) > 0
    for summary in result.lens_summaries.values():
        assert "offline/fallback mode" in summary


def test_strands_fallback_review() -> None:
    harness = StrandsReviewHarness()
    config = ReviewerConfig(harness="strands")
    result = harness.review(
        diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new",
        context="Repo context",
        config=config,
    )
    assert result.recommendation in [Recommendation.APPROVE, Recommendation.COMMENT]
    assert "Strands" in result.summary or "Strands" in result.test_integrity_notes


def test_maf_fallback_review() -> None:
    harness = MafReviewHarness()
    config = ReviewerConfig(harness="maf")
    result = harness.review(
        diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new",
        context="Repo context",
        config=config,
    )
    assert result.recommendation in [Recommendation.APPROVE, Recommendation.COMMENT]
    assert "Microsoft Agent Framework" in result.summary or "MAF" in result.summary


def test_maf_multi_lens_turn_execution() -> None:
    from ci_code_reviewer.lenses import ReviewLensConfig

    harness = MafReviewHarness()
    config = ReviewerConfig(
        harness="maf",
        lenses=[
            ReviewLensConfig(
                name="sql_lens",
                description="Database audits",
                prompt="Check SQL queries",
                file_patterns=["src/db/**"],
            ),
            ReviewLensConfig(
                name="general_lens",
                description="General audit",
                prompt="Check general safety",
                file_patterns=[],
            ),
        ],
    )
    diff = """
--- a/src/db/queries.py
+++ b/src/db/queries.py
@@ -1,2 +1,2 @@
-def get_user(): pass
+def get_user(id): pass
"""
    assessment = harness.review(diff=diff, context="ADR 001", config=config)
    assert "sql_lens" in assessment.lens_summaries
    assert "general_lens" in assessment.lens_summaries
    assert "MAF" in assessment.summary or "Microsoft Agent Framework" in assessment.summary
