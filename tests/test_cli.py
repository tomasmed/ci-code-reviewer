"""Tests for CLI entrypoint and commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ci_code_reviewer.cli import app
from ci_code_reviewer.models import Recommendation, ReviewAssessment

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ci-code-reviewer version:" in result.stdout


def test_cli_review_missing_arguments() -> None:
    result = runner.invoke(app, ["review"])
    assert result.exit_code == 1
    assert "Must specify either --pr <num> or --diff-file <path>" in result.stdout


def test_cli_review_diff_file_dry_run(tmp_path: Path) -> None:
    diff_file = tmp_path / "test.diff"
    diff_file.write_text(
        "--- a/src/app.py\n+++ b/src/app.py\n@@ -1,2 +1,2 @@\n-def run(): pass\n+def run(): return 42\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["review", "--diff-file", str(diff_file), "--dry-run", "--harness", "native"],
    )
    assert result.exit_code == 0
    assert "Diff Evaluated" in result.stdout or "Review Assessment" in result.stdout
    assert "DRY RUN MODE" in result.stdout


def test_cli_review_pr_dry_run() -> None:
    mock_diff = "--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-old\n+new\n"
    mock_info = {
        "head_sha": "abc123commit",
        "base_ref": "main",
        "title": "Update app",
        "author": "developer",
    }

    with (
        patch("ci_code_reviewer.cli.GitHubClient") as mock_client_cls,
        patch.dict("os.environ", {"GITHUB_REPOSITORY": "testorg/testrepo"}),
    ):
        mock_client = MagicMock()
        mock_client.get_pr_diff.return_value = mock_diff
        mock_client.get_pr_info.return_value = mock_info
        mock_client_cls.return_value = mock_client

        result = runner.invoke(app, ["review", "--pr", "12", "--dry-run"])
        assert result.exit_code == 0
        assert "Pull Request #12" in result.stdout
        assert "DRY RUN MODE" in result.stdout
        # Did not post review in dry run
        assert mock_client.post_review.call_count == 0


def test_cli_review_pr_publish_with_vote() -> None:
    mock_diff = "--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-old\n+new\n"
    mock_info = {
        "head_sha": "abc123commit",
        "base_ref": "main",
        "title": "Update app",
        "author": "developer",
    }
    mock_assessment = ReviewAssessment(
        summary="Clean changes.",
        recommendation=Recommendation.APPROVE,
        critical_findings=[],
        suggestions=[],
        test_integrity_notes="",
        lens_summaries={},
    )

    with (
        patch("ci_code_reviewer.cli.GitHubClient") as mock_client_cls,
        patch("ci_code_reviewer.cli.get_harness") as mock_get_harness,
        patch.dict(
            "os.environ",
            {
                "GITHUB_REPOSITORY": "testorg/testrepo",
                "GITHUB_TOKEN": "ghp_mock_token",
            },
        ),
    ):
        mock_client = MagicMock()
        mock_client.get_pr_diff.return_value = mock_diff
        mock_client.get_pr_info.return_value = mock_info
        mock_client.post_review.return_value = {"id": 101, "state": "APPROVED"}
        mock_client_cls.return_value = mock_client

        mock_harness = MagicMock()
        mock_harness.review.return_value = mock_assessment
        mock_get_harness.return_value = mock_harness

        result = runner.invoke(app, ["review", "--pr", "12", "--emit-vote"])
        assert result.exit_code == 0
        assert mock_client.post_review.call_count == 1
        _, kwargs = mock_client.post_review.call_args
        assert kwargs["voting"].enabled is True
        assert kwargs["commit_sha"] == "abc123commit"
