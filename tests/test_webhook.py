"""Integration tests for the FastAPI webhook endpoint."""

import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.api.server import app

WEBHOOK_SECRET = "test-secret"

SAMPLE_PAYLOAD = {
    "action": "opened",
    "repository": {"full_name": "owner/repo"},
    "pull_request": {"number": 42},
}


def make_signature(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET)


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_webhook_invalid_signature(mock_settings):
    body = json.dumps(SAMPLE_PAYLOAD).encode()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/webhook/github",
            content=body,
            headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": "sha256=bad"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_ignores_non_pr_events(mock_settings):
    body = b"{}"
    sig = make_signature(body)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/webhook/github",
            content=body,
            headers={"X-GitHub-Event": "push", "X-Hub-Signature-256": sig},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_webhook_accepts_valid_pr_event(mock_settings):
    body = json.dumps(SAMPLE_PAYLOAD).encode()
    sig = make_signature(body)

    with patch("app.api.server.trigger_review", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/webhook/github",
                content=body,
                headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": sig},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["pr"] == 42
