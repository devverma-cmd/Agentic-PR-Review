"""
LangGraph graph definition for the PR review pipeline.

Graph shape:
  fetch_pr → planner → [fan-out to specialists] → aggregator → comment_generator → post_review
"""

from __future__ import annotations
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.models import PRReviewState, ReviewPlan
from app.agents import (
    fetch_pr_agent,
    planner_agent,
    bug_detector_agent,
    security_scanner_agent,
    performance_analyzer_agent,
    code_smell_agent,
    aggregator_agent,
    comment_generator_agent,
    post_comments_agent,
)
from app.utils import get_logger

logger = get_logger(__name__)


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_planner(state: PRReviewState) -> list[str]:
    """
    Fan-out: return list of agent nodes to run in parallel based on the plan.
    LangGraph's Send() API will run these concurrently.
    """
    plan: ReviewPlan = state.get("plan")  # type: ignore[assignment]
    if plan is None:
        return ["aggregator"]

    targets = []
    if plan.run_bug_detection:
        targets.append("bug_detector")
    if plan.run_security_scan:
        targets.append("security_scanner")
    if plan.run_performance_analysis:
        targets.append("performance_analyzer")
    if plan.run_smell_check:
        targets.append("code_smell")

    return targets if targets else ["aggregator"]


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(checkpointer=None) -> StateGraph:
    builder = StateGraph(PRReviewState)

    # Register nodes
    builder.add_node("fetch_pr", fetch_pr_agent)
    builder.add_node("planner", planner_agent)
    builder.add_node("bug_detector", bug_detector_agent)
    builder.add_node("security_scanner", security_scanner_agent)
    builder.add_node("performance_analyzer", performance_analyzer_agent)
    builder.add_node("code_smell", code_smell_agent)
    builder.add_node("aggregator", aggregator_agent)
    builder.add_node("comment_generator", comment_generator_agent)
    builder.add_node("post_review", post_comments_agent)

    # Linear edges
    builder.set_entry_point("fetch_pr")
    builder.add_edge("fetch_pr", "planner")

    # Conditional fan-out from planner
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "bug_detector": "bug_detector",
            "security_scanner": "security_scanner",
            "performance_analyzer": "performance_analyzer",
            "code_smell": "code_smell",
            "aggregator": "aggregator",   # skip specialists
        },
    )

    # All specialists converge at aggregator
    for specialist in ["bug_detector", "security_scanner", "performance_analyzer", "code_smell"]:
        builder.add_edge(specialist, "aggregator")

    builder.add_edge("aggregator", "comment_generator")
    builder.add_edge("comment_generator", "post_review")
    builder.add_edge("post_review", END)

    return builder.compile(checkpointer=checkpointer)


# ── Compiled graph (module-level singleton) ───────────────────────────────────

_checkpointer = MemorySaver()
graph = build_graph(checkpointer=_checkpointer)
