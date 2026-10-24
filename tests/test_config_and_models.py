"""Tests for configuration, models, and CLI."""

from pathlib import Path

from typer.testing import CliRunner

from ci_code_reviewer import __version__
from ci_code_reviewer.cli import app
from ci_code_reviewer.config import ReviewerConfig
from ci_code_reviewer.models import Recommendation, ReviewAssessment, ReviewComment

runner = CliRunner()


def test_version_cli() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_default_config() -> None:
    config = ReviewerConfig()
    assert config.version == "1"
    assert "anthropic/claude-3-5-sonnet-20241022" in config.model
    assert config.rules.require_tests is True
    assert config.rules.check_security is True


def test_config_load_custom(tmp_path: Path) -> None:
    custom_yaml = tmp_path / ".ci-reviewer.yml"
    custom_yaml.write_text(
        """
version: "1"
model: "openai/gpt-4o"
rules:
  require_tests: false
  custom_guidelines:
    - "No raw SQL queries without ORM"
"""
    )
    loaded = ReviewerConfig.load(custom_yaml)
    assert loaded.model == "openai/gpt-4o"
    assert loaded.rules.require_tests is False
    assert len(loaded.rules.custom_guidelines) == 1
    assert "No raw SQL" in loaded.rules.custom_guidelines[0]


def test_models_serialization() -> None:
    assessment = ReviewAssessment(
        summary="PR adds login feature.",
        recommendation=Recommendation.APPROVE,
        critical_findings=[],
        suggestions=[
            ReviewComment(
                file_path="src/auth.py",
                line_number=42,
                side="RIGHT",
                severity="suggestion",
                title="Use secrets.compare_digest",
                body="Mitigate timing attacks.",
            )
        ],
        test_integrity_notes="High quality unit tests included.",
    )
    assert assessment.recommendation == Recommendation.APPROVE
    assert len(assessment.suggestions) == 1
    dumped = assessment.model_dump()
    assert dumped["recommendation"] == "APPROVE"
    assert dumped["suggestions"][0]["line_number"] == 42
