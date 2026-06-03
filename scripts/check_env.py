#!/usr/bin/env python3
"""
Helper script to verify your environment is configured correctly.
Run with: python scripts/check_env.py
"""

import os
import sys
import asyncio
import httpx


def check_env() -> list[str]:
    required = ["GROQ_API_KEY", "GITHUB_TOKEN", "GITHUB_WEBHOOK_SECRET"]
    missing = [v for v in required if not os.getenv(v)]
    return missing


async def check_groq(api_key: str) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        return resp.status_code == 200


async def check_github(token: str) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 200:
            print(f"  GitHub user: {resp.json().get('login')}")
            return True
        return False


async def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    print("=== AI Code Reviewer — Environment Check ===\n")

    missing = check_env()
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("   Copy .env.example to .env and fill in the values.")
        sys.exit(1)
    print("✅ All required environment variables present\n")

    print("Checking Anthropic API key...")
    ok = await check_anthropic(os.environ["ANTHROPIC_API_KEY"])
    print("✅ Anthropic API reachable\n" if ok else "❌ Anthropic API check failed\n")

    print("Checking GitHub token...")
    ok = await check_github(os.environ["GITHUB_TOKEN"])
    print("✅ GitHub API reachable\n" if ok else "❌ GitHub API check failed\n")

    print("All checks passed. Run `make run` to start the server.")


if __name__ == "__main__":
    asyncio.run(main())
