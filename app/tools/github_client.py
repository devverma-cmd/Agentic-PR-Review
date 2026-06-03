"""GitHub REST API client for fetching PR data and posting reviews."""

from __future__ import annotations
import httpx
from app.config import get_settings
from app.models import PRMetadata, ChangedFile, InlineComment
from app.utils import get_logger

logger = get_logger(__name__)

GITHUB_API = "https://api.github.com"


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def fetch_pr_metadata(repo: str, pr_number: int) -> PRMetadata:
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        data = resp.json()

    return PRMetadata(
        repo_full_name=data["base"]["repo"]["full_name"],
        pr_number=data["number"],
        pr_title=data["title"],
        pr_author=data["user"]["login"],
        head_sha=data["head"]["sha"],
        base_branch=data["base"]["ref"],
        head_branch=data["head"]["ref"],
        html_url=data["html_url"],
    )


async def fetch_pr_diff(repo: str, pr_number: int) -> str:
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={**_headers(), "Accept": "application/vnd.github.diff"},
        )
        resp.raise_for_status()
        return resp.text


async def fetch_pr_files(repo: str, pr_number: int) -> list[ChangedFile]:
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/files"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers(), params={"per_page": 100})
        resp.raise_for_status()
        data = resp.json()

    files = []
    for item in data:
        files.append(
            ChangedFile(
                filename=item["filename"],
                language=_detect_language(item["filename"]),
                patch=item.get("patch"),
                additions=item.get("additions", 0),
                deletions=item.get("deletions", 0),
                status=item.get("status", "modified"),
            )
        )
    return files


async def post_pr_review(
    repo: str,
    pr_number: int,
    head_sha: str,
    summary_body: str,
    inline_comments: list[InlineComment],
    event: str = "COMMENT",  # COMMENT | REQUEST_CHANGES | APPROVE
) -> dict:
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/reviews"

    comments_payload = []
    for c in inline_comments:
        entry: dict = {"path": c.path, "body": c.body}
        if c.position is not None:
            entry["position"] = c.position
        elif c.line is not None:
            entry["line"] = c.line
            entry["side"] = "RIGHT"
        comments_payload.append(entry)

    payload = {
        "commit_id": head_sha,
        "body": summary_body,
        "event": event,
        "comments": comments_payload,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=_headers())
        if resp.status_code not in (200, 201):
            logger.error("github_review_post_failed", status=resp.status_code, body=resp.text)
        resp.raise_for_status()
        return resp.json()


def _detect_language(filename: str) -> str | None:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript", ".go": "go",
        ".rs": "rust", ".java": "java", ".rb": "ruby", ".php": "php",
        ".cs": "csharp", ".cpp": "cpp", ".c": "c", ".kt": "kotlin",
        ".swift": "swift", ".sh": "bash", ".yaml": "yaml", ".yml": "yaml",
        ".json": "json", ".sql": "sql", ".tf": "terraform",
    }
    for ext, lang in ext_map.items():
        if filename.endswith(ext):
            return lang
    return None
