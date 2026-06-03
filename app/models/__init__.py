"""Core data models for the review pipeline."""

from __future__ import annotations
import operator
from typing import Annotated, Literal, TypedDict
from pydantic import BaseModel, Field


# ── Finding ───────────────────────────────────────────────────────────────────

SeverityLevel = Literal["critical", "high", "medium", "low"]
Category = Literal["bug", "security", "performance", "smell"]


class Finding(BaseModel):
    """A single issue found by a specialist agent."""

    file: str = Field(..., description="Relative file path in the repo")
    line: int = Field(..., description="Line number in the new file version")
    severity: SeverityLevel
    category: Category
    title: str = Field(..., max_length=120)
    description: str
    suggestion: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


# ── PR Metadata ───────────────────────────────────────────────────────────────

class PRMetadata(BaseModel):
    repo_full_name: str        # "owner/repo"
    pr_number: int
    pr_title: str
    pr_author: str
    head_sha: str
    base_branch: str
    head_branch: str
    html_url: str


class ChangedFile(BaseModel):
    filename: str
    language: str | None = None   # detected from extension
    patch: str | None = None      # raw git diff patch for this file
    additions: int = 0
    deletions: int = 0
    status: str = "modified"      # added | modified | removed | renamed


# ── Review Plan ───────────────────────────────────────────────────────────────

class ReviewPlan(BaseModel):
    run_bug_detection: bool = True
    run_security_scan: bool = True
    run_performance_analysis: bool = True
    run_smell_check: bool = True
    skip_reason: str | None = None


# ── GitHub Comment ────────────────────────────────────────────────────────────

class InlineComment(BaseModel):
    path: str
    position: int | None = None   # diff position (preferred)
    line: int | None = None       # fallback line number
    body: str


# ── LangGraph State ───────────────────────────────────────────────────────────
#
# Keys written by PARALLEL agents must use Annotated[list, operator.add]
# so LangGraph merges them instead of throwing INVALID_CONCURRENT_GRAPH_UPDATE.
#
class PRReviewState(TypedDict, total=False):
    """Shared state passed through every node in the LangGraph graph."""

    # Populated by fetch_pr (single writer — no annotation needed)
    pr_metadata: PRMetadata
    diff: str
    files: list[ChangedFile]

    # Populated by planner (single writer)
    plan: ReviewPlan

    # ✅ Annotated with operator.add — parallel agents each append their list
    # LangGraph will concatenate the lists from all parallel branches
    bug_findings: Annotated[list[Finding], operator.add]
    security_findings: Annotated[list[Finding], operator.add]
    performance_findings: Annotated[list[Finding], operator.add]
    smell_findings: Annotated[list[Finding], operator.add]

    # Populated by aggregator (single writer)
    all_findings: list[Finding]
    ranked_findings: list[Finding]

    # Populated by comment generator (single writer)
    inline_comments: list[InlineComment]
    summary_comment: str

    # Populated by post agent (single writer)
    review_posted: bool
    review_url: str | None
    error: str | None
