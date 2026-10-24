"""Tests for GitHub REST API client, PR diff fetching, and review publishing."""

import httpx
import pytest

from ci_code_reviewer.config import VotingConfig
from ci_code_reviewer.integrations.github import (
    GitHubClient,
    format_review_body,
    resolve_review_event,
)
from ci_code_reviewer.models import (
    Recommendation,
    ReviewAssessment,
    ReviewComment,
)


@pytest.fixture
def sample_assessment() -> ReviewAssessment:
    return ReviewAssessment(
        summary="PR adds discount calculation helper.",
        recommendation=Recommendation.REQUEST_CHANGES,
        critical_findings=[
            ReviewComment(
                file_path="src/helpers.py",
                line_number=15,
                severity="blocker",
                lens="security_owasp",
                title="Input parameter unvalidated",
                body="Ensure rate is non-negative.",
            )
        ],
        suggestions=[
            ReviewComment(
                file_path="src/helpers.py",
                line_number=20,
                severity="suggestion",
                lens="architecture_adrs",
                title="Extract constant",
                body="Extract default cap to constants module.",
            )
        ],
        test_integrity_notes="Tests were modified in tests/test_helpers.py.",
        lens_summaries={
            "security_owasp": "Detected 1 blocker.",
            "architecture_adrs": "Clean architectural boundaries.",
        },
    )


def test_resolve_review_event_disabled_voting() -> None:
    voting = VotingConfig(enabled=False)
    assert resolve_review_event(Recommendation.APPROVE, voting) == "COMMENT"
    assert resolve_review_event(Recommendation.REQUEST_CHANGES, voting) == "COMMENT"
    assert resolve_review_event(Recommendation.COMMENT, voting) == "COMMENT"


def test_resolve_review_event_enabled_voting() -> None:
    voting = VotingConfig(enabled=True, allow_approve=True, allow_request_changes=True)
    assert resolve_review_event(Recommendation.APPROVE, voting) == "APPROVE"
    assert resolve_review_event(Recommendation.REQUEST_CHANGES, voting) == "REQUEST_CHANGES"
    assert resolve_review_event(Recommendation.COMMENT, voting) == "COMMENT"

    # Restricted approve
    strict_voting = VotingConfig(enabled=True, allow_approve=False, allow_request_changes=True)
    assert resolve_review_event(Recommendation.APPROVE, strict_voting) == "COMMENT"
    assert resolve_review_event(Recommendation.REQUEST_CHANGES, strict_voting) == "REQUEST_CHANGES"


def test_format_review_body(sample_assessment: ReviewAssessment) -> None:
    body = format_review_body(
        sample_assessment,
        blast_radius_context="### ⚠️ Downstream Workspace References\n- `src/billing.py:10`",
        unanchored_comments=[],
    )
    assert "## 🤖 CI Code Review Assessment" in body
    assert "PR adds discount calculation helper." in body
    assert "security_owasp" in body
    assert "Downstream Workspace References" in body
    assert "src/billing.py:10" in body


def test_github_client_get_pr_diff() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/octocat/hello-world/pulls/42"
        assert request.headers.get("Accept") == "application/vnd.github.v3.diff"
        return httpx.Response(200, text="diff --git a/file.py b/file.py\n+new line")

    transport = httpx.MockTransport(handler)
    client = GitHubClient(token="ghp_fake_token", transport=transport)
    diff = client.get_pr_diff(repo="octocat/hello-world", pr_number=42)
    assert "+new line" in diff


def test_github_client_get_pr_info() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/octocat/hello-world/pulls/42"
        return httpx.Response(
            200,
            json={
                "head": {"sha": "abc123commit"},
                "base": {"ref": "main"},
                "title": "Add helper",
                "user": {"login": "dev_user"},
            },
        )

    transport = httpx.MockTransport(handler)
    client = GitHubClient(token="ghp_fake_token", transport=transport)
    info = client.get_pr_info(repo="octocat/hello-world", pr_number=42)
    assert info["head_sha"] == "abc123commit"
    assert info["base_ref"] == "main"
    assert info["author"] == "dev_user"


def test_github_client_post_review_success(sample_assessment: ReviewAssessment) -> None:
    captured_payload: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        if request.url.path == "/repos/octocat/hello-world/pulls/42/reviews":
            import json

            captured_payload = json.loads(request.content.decode("utf-8"))
            return httpx.Response(201, json={"id": 999, "state": captured_payload.get("event")})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = GitHubClient(token="ghp_fake_token", transport=transport)

    voting = VotingConfig(enabled=True)
    res = client.post_review(
        repo="octocat/hello-world",
        pr_number=42,
        commit_sha="abc123commit",
        assessment=sample_assessment,
        voting=voting,
    )

    assert res["id"] == 999
    assert captured_payload["commit_id"] == "abc123commit"
    assert captured_payload["event"] == "REQUEST_CHANGES"
    assert len(captured_payload["comments"]) == 2
    first_comment = captured_payload["comments"][0]
    assert first_comment["path"] == "src/helpers.py"
    assert first_comment["line"] == 15
    assert "[Lens: security_owasp]" in first_comment["body"]


def test_github_client_post_review_422_fallback_recovery(
    sample_assessment: ReviewAssessment,
) -> None:
    call_count = 0
    final_payload: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count, final_payload
        call_count += 1
        import json

        payload = json.loads(request.content.decode("utf-8"))
        # First call with inline comments fails with 422
        if call_count == 1 and payload.get("comments"):
            return httpx.Response(
                422,
                json={"message": "Validation Failed", "errors": ["line must be part of the diff"]},
            )
        # Fallback call with empty comments succeeds
        final_payload = payload
        return httpx.Response(201, json={"id": 1000, "state": payload.get("event")})

    transport = httpx.MockTransport(handler)
    client = GitHubClient(token="ghp_fake_token", transport=transport)

    voting = VotingConfig(enabled=True)
    res = client.post_review(
        repo="octocat/hello-world",
        pr_number=42,
        commit_sha="abc123commit",
        assessment=sample_assessment,
        voting=voting,
    )

    assert res["id"] == 1000
    assert call_count == 2
    # Verify fallback posted without comments array and preserved findings in body
    assert final_payload["comments"] == []
    assert "Unanchored Findings" in final_payload["body"]
    assert "Input parameter unvalidated" in final_payload["body"]
