"""High-level runner that invokes the LangGraph review graph."""

from __future__ import annotations
import uuid
from app.graph.review_graph import graph
from app.models import PRReviewState, PRMetadata
from app.utils import get_logger

logger = get_logger(__name__)


async def run_review(repo: str, pr_number: int) -> PRReviewState:
    """
    Entry point called by the FastAPI webhook handler.
    Initialises state with minimal PR info and lets fetch_pr fill the rest.
    """
    thread_id = f"{repo.replace('/', '_')}_pr{pr_number}_{uuid.uuid4().hex[:8]}"

    initial_state: PRReviewState = {
        "pr_metadata": PRMetadata(  # type: ignore[typeddict-item]
            repo_full_name=repo,
            pr_number=pr_number,
            pr_title="",
            pr_author="",
            head_sha="",
            base_branch="",
            head_branch="",
            html_url="",
        ),
    }

    config = {"configurable": {"thread_id": thread_id}}

    logger.info("graph_run_start", repo=repo, pr=pr_number, thread=thread_id)

    final_state: PRReviewState = await graph.ainvoke(initial_state, config=config)  # type: ignore

    logger.info(
        "graph_run_done",
        repo=repo,
        pr=pr_number,
        posted=final_state.get("review_posted"),
        findings=len(final_state.get("ranked_findings", [])),
        error=final_state.get("error"),
    )

    return final_state
