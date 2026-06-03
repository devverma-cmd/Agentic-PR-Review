# AI-Powered Code Review Assistant

A LangGraph-based multi-agent system that integrates with GitHub/GitLab to automatically review pull requests — detecting bugs, security vulnerabilities, performance bottlenecks, and code smells.

## Architecture

```
GitHub Webhook → FastAPI → LangGraph Graph
                               │
                          ┌────▼─────┐
                          │ PR Fetch │
                          └────┬─────┘
                          ┌────▼─────┐
                          │ Planner  │
                          └────┬─────┘
              ┌───────┬────────┼────────┬───────┐
         ┌────▼───┐ ┌─▼──────┐ ┌──────▼─┐ ┌───▼─────┐
         │  Bug   │ │Security│ │  Perf  │ │  Smell  │
         └────┬───┘ └─┬──────┘ └──────┬─┘ └───┬─────┘
              └───────┴────────┬───────┴───────┘
                          ┌────▼──────┐
                          │Aggregator │
                          └────┬──────┘
                          ┌────▼──────┐
                          │ Generator │
                          └────┬──────┘
                          ┌────▼──────┐
                          │  Post PR  │
                          └───────────┘
```

## Project Structure

```
ai-code-reviewer/
├── app/
│   ├── agents/          # Individual LangGraph agent nodes
│   ├── graph/           # LangGraph graph definition & routing
│   ├── tools/           # GitHub API, diff parsing tools
│   ├── models/          # Pydantic state & data models
│   ├── api/             # FastAPI webhook server
│   └── utils/           # Helpers, formatters, logger
├── tests/               # Unit & integration tests
├── scripts/             # Setup and utility scripts
├── docs/                # Additional documentation
├── .env.example         # Environment variable template
├── pyproject.toml       # Dependencies
└── Makefile             # Common dev commands
```

## Quick Start

```bash
# 1. Clone and install
git clone <your-repo>
cd ai-code-reviewer
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, GITHUB_TOKEN, GITHUB_WEBHOOK_SECRET

# 3. Run the server
make run

# 4. Expose locally with ngrok (for GitHub webhook testing)
make tunnel
```

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GITHUB_TOKEN` | GitHub PAT or App installation token |
| `GITHUB_WEBHOOK_SECRET` | Secret for webhook signature verification |
| `GITHUB_APP_ID` | (Optional) GitHub App ID |
| `GITHUB_APP_PRIVATE_KEY` | (Optional) GitHub App private key path |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` (default: `INFO`) |
| `MAX_FILES_PER_REVIEW` | Limit files reviewed per PR (default: `20`) |
| `SEVERITY_THRESHOLD` | Min severity to post: `low`/`medium`/`high` (default: `low`) |

## How It Works

1. **Webhook received** — GitHub sends a `pull_request` event when a PR is opened or updated.
2. **PR Fetcher** — fetches the diff, file list, and metadata via GitHub REST API.
3. **Planner** — inspects changed files and decides which specialist agents to activate.
4. **Parallel agents** — Bug Detector, Security Scanner, Performance Analyzer, and Code Smell checker each analyze the diff independently using Claude.
5. **Aggregator** — deduplicates findings, scores severity, and ranks them.
6. **Comment Generator** — formats findings as inline GitHub review comments + a summary.
7. **Post to PR** — submits a GitHub Pull Request Review with inline annotations.
