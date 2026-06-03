"""Agent: detects performance bottlenecks and inefficiencies."""

from app.models import PRReviewState, Finding
from app.agents.base import call_llm_json
from app.tools import build_diff_context
from app.utils import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a performance engineering expert.
Analyze the provided code diff and identify performance bottlenecks including:
- N+1 query problems (database queries inside loops)
- Missing database indexes or inefficient queries
- Unnecessary repeated computation inside loops
- Inefficient data structures (list scan where dict/set lookup is O(1))
- Synchronous blocking calls in async contexts
- Large memory allocations or unnecessary data copies
- Missing caching for expensive repeated operations
- Unoptimized algorithm complexity (O(n²) where O(n log n) is possible)
- Excessive serialization/deserialization
- Unnecessary network round trips
- Missing pagination on large dataset queries
- Unbounded loops or missing early exits

Return a JSON array of findings. Each finding must have exactly these fields:
{
  "file": "<relative file path>",
  "line": <integer line number in the NEW file>,
  "severity": "<critical|high|medium|low>",
  "category": "performance",
  "title": "<short title under 80 chars>",
  "description": "<explanation of the bottleneck and its impact>",
  "suggestion": "<concrete optimized code or approach>",
  "confidence": <float 0.0-1.0>
}

Return ONLY the JSON array, no markdown, no preamble."""


async def performance_analyzer_agent(state: PRReviewState) -> PRReviewState:
    files = state.get("files", [])
    diff_context = build_diff_context(files)

    if not diff_context.strip():
        return {"performance_findings": []}

    logger.info("performance_analyzer_start", chars=len(diff_context))

    raw = await call_llm_json(
        system=SYSTEM_PROMPT,
        user=f"Review this diff for performance issues:\n\n{diff_context}",
    )

    findings = []
    for item in raw if isinstance(raw, list) else []:
        try:
            findings.append(Finding(**{**item, "category": "performance"}))
        except Exception as e:
            logger.warning("perf_finding_parse_error", error=str(e), item=item)

    logger.info("performance_analyzer_done", findings=len(findings))
    return {"performance_findings": findings}
