"""Data models and schemas for CI Code Reviewer."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Recommendation(StrEnum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


class ReviewComment(BaseModel):
    file_path: str = Field(description="Relative path of the target file.")
    line_number: int | None = Field(default=None, description="Line number in the new diff.")
    side: Literal["LEFT", "RIGHT"] = Field(
        default="RIGHT", description="Diff side for review comment."
    )
    severity: Literal["blocker", "suggestion", "note"] = Field(
        default="suggestion", description="Finding severity."
    )
    lens: str | None = Field(
        default=None,
        description="The specific review lens (sub-agent turn) that identified this finding.",
    )
    title: str = Field(description="Short title or rule violated.")
    body: str = Field(description="Detailed explanation and remediation suggestion.")


class LensTurnResult(BaseModel):
    """Structured output from a single review lens sub-agent turn."""

    lens_name: str = Field(description="Name of the lens evaluated.")
    summary: str = Field(default="", description="Summary of findings from this lens.")
    findings: list[ReviewComment] = Field(
        default_factory=list, description="List of comments produced by this lens."
    )
    has_blockers: bool = Field(
        default=False, description="True if any blocker was detected by this lens."
    )


class ReviewAssessment(BaseModel):
    summary: str = Field(description="High-level summary of what the PR accomplishes.")
    recommendation: Recommendation = Field(
        description="Final PR recommendation: APPROVE, REQUEST_CHANGES, or COMMENT."
    )
    critical_findings: list[ReviewComment] = Field(
        default_factory=list, description="Blocker issues that must be addressed."
    )
    suggestions: list[ReviewComment] = Field(
        default_factory=list, description="Non-blocking improvements."
    )
    test_integrity_notes: str = Field(
        default="", description="Analysis of test coverage quality and anti-lazy-assert check."
    )
    lens_summaries: dict[str, str] = Field(
        default_factory=dict,
        description="Per-lens summary notes produced by each sub-agent turn.",
    )
