"""Agent: inspects changed files and builds a review plan."""

from app.models import PRReviewState, ReviewPlan, ChangedFile
from app.utils import get_logger

logger = get_logger(__name__)

# Languages where security scanning is particularly valuable
SECURITY_SENSITIVE = {"python", "javascript", "typescript", "php", "ruby", "java", "csharp", "go"}

# Languages where performance analysis is meaningful
PERFORMANCE_RELEVANT = {"python", "javascript", "typescript", "java", "go", "rust", "cpp", "c"}

# Config / data only — skip most analysis
CONFIG_ONLY_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".ini", ".env", ".xml", ".md"}


def _is_config_only(files: list[ChangedFile]) -> bool:
    return all(
        any(f.filename.endswith(ext) for ext in CONFIG_ONLY_EXTENSIONS)
        for f in files
    )


async def planner_agent(state: PRReviewState) -> PRReviewState:
    files = state.get("files", [])
    languages = {f.language for f in files if f.language}

    logger.info("planner_start", files=len(files), languages=list(languages))

    if not files or _is_config_only(files):
        plan = ReviewPlan(
            run_bug_detection=False,
            run_security_scan=False,
            run_performance_analysis=False,
            run_smell_check=True,  # still worth checking style
            skip_reason="Config/data-only PR — full analysis skipped",
        )
    else:
        plan = ReviewPlan(
            run_bug_detection=True,
            run_security_scan=bool(languages & SECURITY_SENSITIVE),
            run_performance_analysis=bool(languages & PERFORMANCE_RELEVANT),
            run_smell_check=True,
        )

    logger.info("planner_done", plan=plan.model_dump())
    return {"plan": plan}
