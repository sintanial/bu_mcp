"""Resolve LLM for browser-use Agent."""

from __future__ import annotations

import os

from browser_use.llm.base import BaseChatModel


def build_llm(
    *,
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
) -> BaseChatModel:
    """Prefer keys from MCP request (HTTP headers or tools/call _meta); else env."""
    oa = (openai_api_key or "").strip() or os.getenv("OPENAI_API_KEY")
    an = (anthropic_api_key or "").strip() or os.getenv("ANTHROPIC_API_KEY")

    if oa:
        from browser_use.llm.openai.chat import ChatOpenAI

        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        return ChatOpenAI(model=model, api_key=oa)

    if an:
        from browser_use.llm.anthropic.chat import ChatAnthropic

        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        return ChatAnthropic(model=model, api_key=an)

    raise RuntimeError(
        "Set X-OpenAI-Api-Key and/or X-Anthropic-Api-Key on the MCP request (HTTP or tools/call _meta), "
        "or OPENAI_API_KEY / ANTHROPIC_API_KEY in the environment."
    )
