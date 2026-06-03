#!/usr/bin/env python3
"""
Manually trigger a review on a real GitHub PR without needing a webhook.

Usage:
    python scripts/trigger_review.py owner/repo 42
"""

import sys
import asyncio


async def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python scripts/trigger_review.py <owner/repo> <pr_number>")
        sys.exit(1)

    repo = sys.argv[1]
    pr_number = int(sys.argv[2])

    from dotenv import load_dotenv
    load_dotenv()

    from app.graph import run_review
    from app.utils import setup_logging
    setup_logging()

    print(f"Running review for PR #{pr_number} in {repo} …")
    state = await run_review(repo, pr_number)

    print(f"\n{'='*50}")
    print(f"Review complete!")
    print(f"  Posted:   {state.get('review_posted')}")
    print(f"  URL:      {state.get('review_url')}")
    print(f"  Findings: {len(state.get('ranked_findings', []))}")
    if state.get("error"):
        print(f"  Error:    {state['error']}")


if __name__ == "__main__":
    asyncio.run(main())
