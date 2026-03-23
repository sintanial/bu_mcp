"""Resolve LLM and Browser Use API keys from MCP request context (HTTP headers or tools/call _meta)."""

from __future__ import annotations

import os
from typing import Any

from mcp.server.lowlevel.server import request_ctx

HEADER_BROWSER_USE = "x-browser-use-api-key"
HEADER_OPENAI = "x-openai-api-key"
HEADER_ANTHROPIC = "x-anthropic-api-key"

_META_SKIP = frozenset({"progressToken", "task"})


def _strip(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip()
    return s or None


def _from_starlette_headers(request: Any) -> tuple[str | None, str | None, str | None]:
    if request is None or not hasattr(request, "headers"):
        return None, None, None
    h = request.headers
    return (
        _strip(h.get(HEADER_OPENAI)),
        _strip(h.get(HEADER_ANTHROPIC)),
        _strip(h.get(HEADER_BROWSER_USE)),
    )


def _from_meta(meta: Any) -> tuple[str | None, str | None, str | None]:
    if meta is None:
        return None, None, None
    if hasattr(meta, "model_dump"):
        d = meta.model_dump(mode="json")
    elif isinstance(meta, dict):
        d = meta
    else:
        return None, None, None
    norm: dict[str, str] = {}
    for k, v in d.items():
        if k in _META_SKIP or v is None:
            continue
        if isinstance(v, str):
            lk = k.lower().replace("_", "-")
            if v.strip():
                norm[lk] = v.strip()
    return (
        norm.get(HEADER_OPENAI),
        norm.get(HEADER_ANTHROPIC),
        norm.get(HEADER_BROWSER_USE),
    )


def _first(*vals: str | None) -> str | None:
    for v in vals:
        if v:
            return v
    return None


def resolve_mcp_api_keys() -> tuple[str | None, str | None, str | None]:
    """OpenAI, Anthropic, Browser Use keys: HTTP headers (streamable HTTP) or params._meta (stdio), then env."""
    env_oa = _strip(os.getenv("OPENAI_API_KEY"))
    env_an = _strip(os.getenv("ANTHROPIC_API_KEY"))
    env_bu = _strip(os.getenv("BROWSER_USE_API_KEY"))

    try:
        ctx = request_ctx.get()
    except LookupError:
        return env_oa, env_an, env_bu

    hdr_oa, hdr_an, hdr_bu = _from_starlette_headers(ctx.request)
    meta_oa, meta_an, meta_bu = _from_meta(ctx.meta)

    return (
        _first(hdr_oa, meta_oa, env_oa),
        _first(hdr_an, meta_an, env_an),
        _first(hdr_bu, meta_bu, env_bu),
    )
