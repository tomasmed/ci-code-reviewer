"""Tests for review harnesses and factory."""

import logging
from unittest.mock import patch

import pytest

from ci_code_reviewer.config import ReviewerConfig
from ci_code_reviewer.harness.factory import HARNESS_REGISTRY, get_harness
from ci_code_reviewer.harness.maf import MafReviewHarness
from ci_code_reviewer.harness.native import NativeReviewHarness
from ci_code_reviewer.harness.strands import StrandsReviewHarness
from ci_code_reviewer.lenses import ReviewLensConfig
from ci_code_reviewer.models import LensTurnResult, Recommendation, ReviewComment


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


def test_native_fallback_review(caplog: pytest.LogCaptureFixture) -> None:
    harness = NativeReviewHarness()
    config = ReviewerConfig(harness="native")
    with caplog.at_level(logging.ERROR):
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
        assert "encountered an error" in summary
        assert "Check CI logs" in summary
        assert "Exception" not in summary
        assert "Traceback" not in summary
    assert any("Review lens" in record.message for record in caplog.records)


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


def test_maf_fallback_review(caplog: pytest.LogCaptureFixture) -> None:
    harness = MafReviewHarness()
    config = ReviewerConfig(harness="maf")
    with caplog.at_level(logging.ERROR):
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
        assert "encountered an error" in summary
        assert "Check CI logs" in summary
        assert "Exception" not in summary
        assert "Traceback" not in summary
    assert any("Review lens" in record.message for record in caplog.records)


def test_native_partial_fallback_review() -> None:
    harness = NativeReviewHarness()
    config = ReviewerConfig(harness="native")

    success_turn = LensTurnResult(
        lens_name="architecture_adrs",
        summary="All architectural patterns confirmed.",
        findings=[
            ReviewComment(
                file_path="src/api.py",
                line_number=10,
                side="RIGHT",
                severity="suggestion",
                title="Consider dependency injection",
                body="Decouple direct instantiation.",
            )
        ],
        has_blockers=False,
    )
    fallback_turn = LensTurnResult(
        lens_name="security_owasp",
        summary="Sub-agent turn for lens 'security_owasp' encountered an error and could not complete review. Check CI logs for details (offline/fallback mode).",
        findings=[],
        has_blockers=False,
    )

    with patch.object(
        harness,
        "_execute_lens_turn",
        side_effect=[success_turn, fallback_turn, fallback_turn],
    ):
        result = harness.review(
            diff="--- a/src/api.py\n+++ b/src/api.py\n@@ -1 +1 @@\n-old\n+new",
            context="context",
            config=config,
        )
        assert result.recommendation == Recommendation.COMMENT
        assert "Found 0 blockers and 1 suggestions" in result.summary
        assert "operated in fallback mode" in result.summary


def test_maf_multi_lens_turn_execution() -> None:
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


def test_harness_empty_lenses_no_false_fallback() -> None:
    native = NativeReviewHarness()
    maf = MafReviewHarness()
    empty_config = ReviewerConfig(lenses=[])

    native_result = native.review(
        diff="--- a/src/api.py\n+++ b/src/api.py\n@@ -1 +1 @@\n-old\n+new",
        context="context",
        config=empty_config,
    )
    assert native_result.recommendation == Recommendation.APPROVE
    assert "fallback mode" not in native_result.summary

    maf_result = maf.review(
        diff="--- a/src/api.py\n+++ b/src/api.py\n@@ -1 +1 @@\n-old\n+new",
        context="context",
        config=empty_config,
    )
    assert maf_result.recommendation == Recommendation.APPROVE
    assert "fallback mode" not in maf_result.summary
