"""Agent: posts the generated review back to GitHub."""

from app.models import PRReviewState
from app.tools import post_pr_review
from app.utils import get_logger

logger = get_logger(__name__)


def _decide_review_event(ranked_findings) -> str:
    """Request changes if any critical finding; otherwise informational comment."""
    severities = {f.severity for f in ranked_findings}
    if "critical" in severities:
        return "REQUEST_CHANGES"
    return "COMMENT"


async def post_comments_agent(state: PRReviewState) -> dict:
    meta = state["pr_metadata"]
    inline = state.get("inline_comments", [])
    summary = state.get("summary_comment", "")
    ranked = state.get("ranked_findings", [])

    review_event = _decide_review_event(ranked)

    logger.info(
        "post_review_start",
        repo=meta.repo_full_name,
        pr=meta.pr_number,
        review_event=review_event,   # ✅ renamed — 'event' is reserved by structlog
        inline_count=len(inline),
    )

    try:
        result = await post_pr_review(
            repo=meta.repo_full_name,
            pr_number=meta.pr_number,
            head_sha=meta.head_sha,
            summary_body=summary,
            inline_comments=inline,
            event=review_event,
        )
        review_url = result.get("html_url")
        logger.info("post_review_done", url=review_url)
        return {"review_posted": True, "review_url": review_url}  # ✅ only own keys

    except Exception as exc:
        logger.error("post_review_failed", error=str(exc))
        return {"review_posted": False, "error": str(exc)}        # ✅ only own keys
