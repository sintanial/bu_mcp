"""MCP tools/call dispatch: validate args and run session / cloud logic."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import mcp.types as types

from bu_mcp.auth_keys import resolve_mcp_api_keys
from bu_mcp.sessions import SessionRegistry, clamp_max_steps


async def handle_tool_call(
    name: str,
    arguments: dict[str, Any],
    *,
    registry: SessionRegistry,
) -> list[types.TextContent]:
    if name == "session_start":
        task = arguments.get("task")
        if not task or not isinstance(task, str):
            raise ValueError("task is required")

        oa, an, bu = resolve_mcp_api_keys()
        raw_idle = arguments.get("idle_timeout_seconds")
        idle_timeout_seconds: int | None
        if raw_idle is None:
            idle_timeout_seconds = None
        else:
            if not isinstance(raw_idle, int):
                raise ValueError("idle_timeout_seconds must be an integer (seconds)")
            idle_timeout_seconds = raw_idle

        st = await registry.create_session(
            task=task,
            max_steps=arguments.get("max_steps"),
            bu_profile_id=arguments.get("bu_profile_id"),
            country_code=arguments.get("country_code"),
            idle_timeout_seconds=idle_timeout_seconds,
            openai_api_key=oa,
            anthropic_api_key=an,
            browser_use_api_key=bu,
        )
        payload = {"session_id": st.id, "live_url": st.live_url}
        return [types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]

    if name == "session_status":
        sid = arguments.get("session_id")
        if not sid or not isinstance(sid, str):
            raise ValueError("session_id is required")
        st = await registry.get(sid)
        if st is None or st.closed:
            raise ValueError("session not found or closed")
        registry.touch_idle_activity(st)
        inc_shot = bool(arguments.get("include_screenshot", False))
        raw_steps = arguments.get("include_steps")
        if raw_steps is None:
            inc_steps: int | None = None
        else:
            inc_steps = int(raw_steps)
        snap = await registry.snapshot(st, include_screenshot=inc_shot, include_steps_raw=inc_steps)
        return [types.TextContent(type="text", text=json.dumps(snap, ensure_ascii=False))]

    if name == "session_supplement":
        sid = arguments.get("session_id")
        task = arguments.get("task")
        if not sid or not isinstance(sid, str):
            raise ValueError("session_id is required")
        if not task or not isinstance(task, str):
            raise ValueError("task is required")
        st = await registry.get(sid)
        if st is None or st.closed:
            raise ValueError("session not found or closed")
        registry.touch_idle_activity(st)
        async with st.lock:
            if st.is_running():
                raise ValueError("session is busy (agent still running); poll session_status and retry")
            ms = clamp_max_steps(None)
            st.runner_task = asyncio.create_task(st.run_agent(task, ms))
        payload = {"session_id": st.id, "live_url": st.live_url}
        return [types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]

    if name == "session_close":
        sid = arguments.get("session_id")
        if not sid or not isinstance(sid, str):
            raise ValueError("session_id is required")
        ok = await registry.close_session(sid)
        payload = {"closed": True} if ok else {"closed": True, "note": "session was already closed"}
        return [types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]

    raise ValueError(f"unknown tool: {name}")
