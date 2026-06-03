"""Agent: detects security vulnerabilities in the diff."""

from app.models import PRReviewState, Finding
from app.agents.base import call_llm_json
from app.tools import build_diff_context
from app.utils import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a security engineer specializing in application security (AppSec).
Analyze the provided code diff and identify security vulnerabilities including:
- Injection attacks: SQL injection, command injection, LDAP injection
- XSS (Cross-Site Scripting) — reflected, stored, DOM-based
- Insecure deserialization
- Hardcoded secrets, API keys, passwords, or tokens
- Broken authentication or session management
- Insecure direct object references (IDOR)
- Sensitive data exposure (PII logged, unencrypted storage)
- Missing authorization checks
- Path traversal vulnerabilities
- Use of deprecated or vulnerable cryptography
- SSRF (Server-Side Request Forgery)
- Open redirects

Map severity to OWASP risk levels: critical = CVSS 9+, high = 7-9, medium = 4-7, low < 4.

Return a JSON array of findings. Each finding must have exactly these fields:
{
  "file": "<relative file path>",
  "line": <integer line number in the NEW file>,
  "severity": "<critical|high|medium|low>",
  "category": "security",
  "title": "<short title under 80 chars>",
  "description": "<explanation of the vulnerability and its impact>",
  "suggestion": "<concrete remediation code or approach>",
  "confidence": <float 0.0-1.0>
}

Return ONLY the JSON array, no markdown, no preamble."""


async def security_scanner_agent(state: PRReviewState) -> PRReviewState:
    files = state.get("files", [])
    diff_context = build_diff_context(files)

    if not diff_context.strip():
        return {"security_findings": []}

    logger.info("security_scanner_start", chars=len(diff_context))

    raw = await call_llm_json(
        system=SYSTEM_PROMPT,
        user=f"Review this diff for security vulnerabilities:\n\n{diff_context}",
    )

    findings = []
    for item in raw if isinstance(raw, list) else []:
        try:
            findings.append(Finding(**{**item, "category": "security"}))
        except Exception as e:
            logger.warning("security_finding_parse_error", error=str(e), item=item)

    logger.info("security_scanner_done", findings=len(findings))
    return {"security_findings": findings}
