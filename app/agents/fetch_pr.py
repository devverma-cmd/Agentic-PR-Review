"""Agent: fetches PR metadata, diff, and file list from GitHub."""

from app.models import PRReviewState
from app.tools import fetch_pr_metadata, fetch_pr_diff, fetch_pr_files, filter_files
from app.config import get_settings
from app.utils import get_logger

logger = get_logger(__name__)


async def fetch_pr_agent(state: PRReviewState) -> PRReviewState:
    """
    Entry node. Fetches all PR data needed for downstream agents.
    Expects state to already contain pr_metadata.repo_full_name and pr_number.
    """
    meta = state["pr_metadata"]
    repo = meta.repo_full_name
    pr_number = meta.pr_number
    settings = get_settings()

    logger.info("fetch_pr_start", repo=repo, pr=pr_number)

    # Fetch full metadata (author, sha, branches, etc.)
    full_meta = await fetch_pr_metadata(repo, pr_number)

    # Fetch raw unified diff
    diff = await fetch_pr_diff(repo, pr_number)

    # Fetch file list with patches
    all_files = await fetch_pr_files(repo, pr_number)
    files = filter_files(all_files, max_files=settings.max_files_per_review)

    logger.info("fetch_pr_done", files=len(files), diff_chars=len(diff))

    return {
        "pr_metadata": full_meta,
        "diff": diff,
        "files": files,
    }
