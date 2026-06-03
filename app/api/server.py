"""FastAPI server — receives GitHub webhook events and triggers the review graph."""

from __future__ import annotations
import asyncio
import hashlib
import hmac
import json
import os

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.graph import run_review
from app.utils import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

# Set DISABLE_WEBHOOK_SIGNATURE=true in .env to skip signature check during local dev
DISABLE_SIGNATURE_CHECK = os.getenv("DISABLE_WEBHOOK_SIGNATURE", "false").lower() == "true"

app = FastAPI(
    title="AI Code Reviewer",
    description="LangGraph-powered pull request review agent",
    version="0.1.0",
)

#CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Signature verification ─────────────────────────────────────────────────────

def verify_github_signature(payload: bytes, signature_header: str | None) -> bool:
    """Validate the X-Hub-Signature-256 header from GitHub."""
    if DISABLE_SIGNATURE_CHECK:
        logger.warning("signature_check_disabled — do not use in production")
        return True

    if not signature_header:
        logger.error("sig_missing — GitHub sent no X-Hub-Signature-256 header")
        return False

    secret = get_settings().github_webhook_secret.encode()
    # ✅ correct: hmac.new(key, msg, digestmod)
    mac = hmac.new(secret, msg=payload, digestmod=hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()

    match = hmac.compare_digest(expected, signature_header)
    if not match:
        logger.error(
            "sig_mismatch",
            expected_prefix=expected[:20],
            received_prefix=signature_header[:20],
            hint="Check that GITHUB_WEBHOOK_SECRET in .env exactly matches what you entered in GitHub webhook settings",
        )
    return match


# ── Background task ────────────────────────────────────────────────────────────

async def trigger_review(repo: str, pr_number: int) -> None:
    try:
        logger.info("review_start", repo=repo, pr=pr_number)
        result = await run_review(repo, pr_number)
        logger.info(
            "review_complete",
            repo=repo,
            pr=pr_number,
            posted=result.get("review_posted"),
            findings=len(result.get("ranked_findings", [])),
            url=result.get("review_url"),
            error=result.get("error"),
        )
    except Exception as exc:
        logger.error("review_pipeline_crashed", repo=repo, pr=pr_number, error=str(exc))


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "signature_check": not DISABLE_SIGNATURE_CHECK}


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    gh_event = request.headers.get("X-GitHub-Event", "unknown")

    logger.info("webhook_incoming", gh_event=gh_event, signature_present=bool(signature))

    if not verify_github_signature(body, signature):
        logger.error("webhook_rejected_bad_signature")
        # Return 200 so GitHub doesn't keep retrying — just drop it
        return JSONResponse({"status": "rejected", "reason": "invalid signature"}, status_code=200)

    if gh_event != "pull_request":
        return JSONResponse({"status": "ignored", "reason": f"gh_event={gh_event}"})

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("webhook_bad_json")
        return JSONResponse({"status": "error", "reason": "invalid JSON"}, status_code=200)

    action = payload.get("action", "")
    logger.info("webhook_pr_action", gh_event=gh_event, action=action)

    # Only review on open / reopen / synchronize (new commits pushed)
    if action not in ("opened", "reopened", "synchronize"):
        return JSONResponse({"status": "ignored", "reason": f"action={action}"})

    repo = payload["repository"]["full_name"]
    pr_number = payload["pull_request"]["number"]

    logger.info("webhook_accepted", repo=repo, pr=pr_number, action=action)

    # Run the review graph in the background — return 200 immediately to GitHub
    background_tasks.add_task(trigger_review, repo, pr_number)

    return JSONResponse({"status": "accepted", "repo": repo, "pr": pr_number})


@app.post("/review/trigger")
async def manual_trigger(repo: str, pr_number: int, background_tasks: BackgroundTasks) -> JSONResponse:
    """
    Manual trigger — no webhook needed. Useful for testing.
    Usage: curl -X POST "http://localhost:8000/review/trigger?repo=owner/repo&pr_number=5"
    """
    logger.info("manual_trigger", repo=repo, pr=pr_number)
    background_tasks.add_task(trigger_review, repo, pr_number)
    return JSONResponse({"status": "triggered", "repo": repo, "pr": pr_number})


@app.get("/debug/config")
async def debug_config() -> JSONResponse:
    """Shows non-sensitive config — helpful for diagnosing issues."""
    s = get_settings()
    return JSONResponse({
        "model_name": s.model_name,
        "max_files_per_review": s.max_files_per_review,
        "severity_threshold": s.severity_threshold,
        "signature_check_enabled": not DISABLE_SIGNATURE_CHECK,
        "github_token_set": bool(s.github_token),
        "groq_api_key_set": bool(s.groq_api_key),
    })


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.api.server:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
