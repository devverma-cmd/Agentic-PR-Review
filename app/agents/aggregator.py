"""Agent: collects findings from all specialists, deduplicates, and ranks them."""

from app.models import PRReviewState, Finding
from app.utils import get_logger, rank_findings, deduplicate_findings
from app.config import get_settings

logger = get_logger(__name__)

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


async def aggregator_agent(state: PRReviewState) -> PRReviewState:
    plan = state.get("plan")
    settings = get_settings()

    all_findings: list[Finding] = []

    if not plan or plan.run_bug_detection:
        all_findings.extend(state.get("bug_findings", []))

    if not plan or plan.run_security_scan:
        all_findings.extend(state.get("security_findings", []))

    if not plan or plan.run_performance_analysis:
        all_findings.extend(state.get("performance_findings", []))

    if not plan or plan.run_smell_check:
        all_findings.extend(state.get("smell_findings", []))

    logger.info("aggregator_raw", total=len(all_findings))

    # Deduplicate overlapping findings (same file + line + category)
    unique = deduplicate_findings(all_findings)

    # Filter by configured severity threshold
    threshold_idx = SEVERITY_ORDER.get(settings.severity_threshold, 3)
    filtered = [f for f in unique if SEVERITY_ORDER[f.severity] <= threshold_idx]

    # Rank by severity then confidence
    ranked = rank_findings(filtered)

    logger.info("aggregator_done", unique=len(unique), after_threshold=len(ranked))

    return {
        "all_findings": unique,
        "ranked_findings": ranked,
    }
