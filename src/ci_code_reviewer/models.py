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
    title: str = Field(description="Short title or rule violated.")
    body: str = Field(description="Detailed explanation and remediation suggestion.")


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
