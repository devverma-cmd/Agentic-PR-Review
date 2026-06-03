"""Agent: detects code smells, style issues, and maintainability problems."""

from app.models import PRReviewState, Finding
from app.agents.base import call_llm_json
from app.tools import build_diff_context
from app.utils import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer focused on code quality and maintainability.
Analyze the provided code diff and identify code smells including:
- Long methods or classes (violates Single Responsibility Principle)
- Deep nesting (more than 3-4 levels of indentation)
- Duplicate code (DRY violations)
- Magic numbers or strings (should be named constants)
- Poor naming (single-letter variables outside loops, misleading names)
- Dead code (unreachable code, unused variables/imports/parameters)
- God objects (classes doing too much)
- Feature envy (method using another class's data excessively)
- Inappropriate intimacy between classes
- Overly complex boolean logic that should be simplified
- Missing or inadequate error handling
- Functions with too many parameters (> 4-5)
- Commented-out code left in the codebase
- Missing docstrings or type annotations on public APIs

Return a JSON array of findings. Each finding must have exactly these fields:
{
  "file": "<relative file path>",
  "line": <integer line number in the NEW file>,
  "severity": "<critical|high|medium|low>",
  "category": "smell",
  "title": "<short title under 80 chars>",
  "description": "<explanation of the smell and why it matters>",
  "suggestion": "<concrete refactoring suggestion or improved code>",
  "confidence": <float 0.0-1.0>
}

Return ONLY the JSON array, no markdown, no preamble."""


async def code_smell_agent(state: PRReviewState) -> PRReviewState:
    files = state.get("files", [])
    diff_context = build_diff_context(files)

    if not diff_context.strip():
        return {"smell_findings": []}

    logger.info("code_smell_start", chars=len(diff_context))

    raw = await call_llm_json(
        system=SYSTEM_PROMPT,
        user=f"Review this diff for code smells and maintainability issues:\n\n{diff_context}",
    )

    findings = []
    for item in raw if isinstance(raw, list) else []:
        try:
            findings.append(Finding(**{**item, "category": "smell"}))
        except Exception as e:
            logger.warning("smell_finding_parse_error", error=str(e), item=item)

    logger.info("code_smell_done", findings=len(findings))
    return {"smell_findings": findings}
