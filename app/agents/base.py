"""Shared LLM invocation helper for all agents — powered by Groq via langchain_groq."""

from __future__ import annotations
import json
import re
from functools import lru_cache
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import get_settings
from app.utils import get_logger

logger = get_logger(__name__)


@lru_cache
def get_client() -> ChatGroq:
    """Return a cached ChatGroq instance."""
    settings = get_settings()
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.model_name,
        max_tokens=settings.max_tokens,
        temperature=0.0,   # deterministic for code review
    )


async def call_llm(system: str, user: str, max_tokens: int | None = None) -> str:
    """Invoke the Groq model and return the text response."""
    client = get_client()
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=user),
    ]
    response = await client.ainvoke(messages)
    return response.content  # type: ignore[return-value]


async def call_llm_json(system: str, user: str) -> list | dict:
    """Invoke the model expecting a JSON response; strips markdown fences."""
    raw = await call_llm(system, user)
    clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("llm_json_parse_failed", raw=raw[:200])
        return []
