"""Agent: detects logic errors, null dereferences, and potential bugs."""

from app.models import PRReviewState, Finding
from app.agents.base import call_llm_json
from app.tools import build_diff_context
from app.utils import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert software engineer specializing in bug detection.
Analyze the provided code diff and identify potential bugs including:
- Null/undefined dereferences
- Off-by-one errors
- Unhandled exceptions or error paths
- Race conditions or concurrency issues
- Incorrect logic or edge cases
- Missing input validation
- Resource leaks (file handles, connections, memory)

Return a JSON array of findings. Each finding must have exactly these fields:
{
  "file": "<relative file path>",
  "line": <integer line number in the NEW file>,
  "severity": "<critical|high|medium|low>",
  "category": "bug",
  "title": "<short title under 80 chars>",
  "description": "<clear explanation of the bug>",
  "suggestion": "<concrete code or approach to fix it>",
  "confidence": <float 0.0-1.0>
}

Return ONLY the JSON array, no markdown, no preamble."""


async def bug_detector_agent(state: PRReviewState) -> PRReviewState:
    files = state.get("files", [])
    diff_context = build_diff_context(files)

    if not diff_context.strip():
        return {"bug_findings": []}

    logger.info("bug_detector_start", chars=len(diff_context))

    raw = await call_llm_json(
        system=SYSTEM_PROMPT,
        user=f"Review this diff for bugs:\n\n{diff_context}",
    )

    findings = []
    for item in raw if isinstance(raw, list) else []:
        try:
            findings.append(Finding(**{**item, "category": "bug"}))
        except Exception as e:
            logger.warning("bug_finding_parse_error", error=str(e), item=item)

    logger.info("bug_detector_done", findings=len(findings))
    return {"bug_findings": findings}
