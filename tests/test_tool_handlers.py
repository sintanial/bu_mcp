"""session_status passes include_steps / include_screenshot into snapshot."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from bu_mcp.tool_handlers import handle_tool_call


class _FakeRegistry:
    """Minimal async registry: only get + snapshot (what handle_tool_call uses)."""

    def __init__(self) -> None:
        self.snapshot_kwargs: dict[str, Any] | None = None

    async def get(self, session_id: str) -> object | None:
        if session_id == "s1":
            return SimpleNamespace(closed=False)
        return None

    async def snapshot(
        self,
        state: object,
        *,
        include_screenshot: bool,
        include_steps_raw: int | None,
    ) -> dict[str, Any]:
        self.snapshot_kwargs = {
            "include_screenshot": include_screenshot,
            "include_steps_raw": include_steps_raw,
        }
        body: dict[str, Any] = {
            "status": "finished",
            "output": "ok",
            "finished_at": "2025-01-01T00:00:00Z",
            "is_success": True,
        }
        if include_steps_raw is not None and include_steps_raw != 0:
            limit = None if include_steps_raw < 0 else include_steps_raw
            body["steps"] = [{"number": 1, "memory": "m"}][: limit or 1]
        return body


@pytest.mark.asyncio
async def test_session_status_include_steps_zero_passes_zero_not_omitted():
    reg = _FakeRegistry()
    out = await handle_tool_call(
        "session_status",
        {"session_id": "s1", "include_steps": 0},
        registry=reg,
    )
    assert reg.snapshot_kwargs is not None
    assert reg.snapshot_kwargs["include_steps_raw"] == 0
    import json

    payload = json.loads(out[0].text)
    assert "steps" not in payload


@pytest.mark.asyncio
async def test_session_status_include_steps_negative_one():
    reg = _FakeRegistry()
    await handle_tool_call(
        "session_status",
        {"session_id": "s1", "include_steps": -1},
        registry=reg,
    )
    assert reg.snapshot_kwargs["include_steps_raw"] == -1


@pytest.mark.asyncio
async def test_session_status_include_screenshot_true():
    reg = _FakeRegistry()
    await handle_tool_call(
        "session_status",
        {"session_id": "s1", "include_screenshot": True},
        registry=reg,
    )
    assert reg.snapshot_kwargs["include_screenshot"] is True


@pytest.mark.asyncio
async def test_session_status_omit_include_steps_is_none():
    reg = _FakeRegistry()
    await handle_tool_call("session_status", {"session_id": "s1"}, registry=reg)
    assert reg.snapshot_kwargs["include_steps_raw"] is None


@pytest.mark.asyncio
async def test_unknown_tool_raises():
    from bu_mcp.sessions import SessionRegistry

    with pytest.raises(ValueError, match="unknown tool"):
        await handle_tool_call("session_foo", {}, registry=SessionRegistry())
