"""Unit tests for bu_mcp.sessions: clamp_max_steps, history helpers, snapshot."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bu_mcp.sessions import (
    BrowserMcpSession,
    SessionRegistry,
    clamp_max_steps,
    history_to_steps,
    last_screenshot_b64,
    progress_output,
    resolve_idle_timeout_seconds,
)


# --- clamp_max_steps ---


def test_clamp_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BU_MCP_DEFAULT_MAX_STEPS", raising=False)
    assert clamp_max_steps(0) == 1
    assert clamp_max_steps(600) == 500
    assert clamp_max_steps(50) == 50


def test_default_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BU_MCP_DEFAULT_MAX_STEPS", "25")
    assert clamp_max_steps(None) == 25


# --- resolve_idle_timeout_seconds ---


def test_idle_timeout_default_and_clamp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BU_MCP_DEFAULT_IDLE_TIMEOUT_SECONDS", raising=False)
    assert resolve_idle_timeout_seconds(None) == 900
    assert resolve_idle_timeout_seconds(120) == 120
    assert resolve_idle_timeout_seconds(1) == 1
    assert resolve_idle_timeout_seconds(9999999) == 604800


def test_idle_timeout_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BU_MCP_DEFAULT_IDLE_TIMEOUT_SECONDS", "600")
    assert resolve_idle_timeout_seconds(None) == 600


# --- history_to_steps, last_screenshot_b64, progress_output ---


def _history_item(
    *,
    url: str | None = "https://a.example/",
    screenshot_path: str | None = None,
    memory: str = "m",
    evaluation_previous_goal: str | None = "ev",
    next_goal: str | None = "ng",
    actions: list | None = None,
):
    h = MagicMock()
    st = MagicMock()
    st.url = url
    st.screenshot_path = screenshot_path
    h.state = st
    mo = MagicMock()
    mo.memory = memory
    mo.evaluation_previous_goal = evaluation_previous_goal
    mo.next_goal = next_goal
    mo.action = actions
    h.model_output = mo
    return h


def test_history_to_steps_empty():
    assert history_to_steps(None, None) == []
    assert history_to_steps(MagicMock(history=[]), None) == []


def test_history_to_steps_full_and_limits():
    items = [_history_item(memory=f"m{i}") for i in range(4)]
    hist = MagicMock()
    hist.history = items

    full = history_to_steps(hist, None)
    assert len(full) == 4
    assert [x["number"] for x in full] == [1, 2, 3, 4]
    assert full[0]["memory"] == "m0"
    assert full[0]["url"] == "https://a.example/"

    last2 = history_to_steps(hist, 2)
    assert len(last2) == 2
    assert last2[0]["number"] == 3
    assert last2[1]["number"] == 4

    last_all = history_to_steps(hist, -1)
    assert len(last_all) == 4


def test_history_to_steps_screenshot_path_in_step():
    h = _history_item(screenshot_path="/tmp/x.png")
    hist = MagicMock()
    hist.history = [h]
    out = history_to_steps(hist, None)
    assert out[0]["screenshot_path"] == "/tmp/x.png"


def test_history_to_steps_actions_model_dump():
    act = MagicMock()
    act.model_dump = lambda exclude_none=True, mode="json": {"name": "click", "index": 1}
    h = _history_item(actions=[act])
    hist = MagicMock()
    hist.history = [h]
    out = history_to_steps(hist, None)
    assert out[0]["actions"] == [{"name": "click", "index": 1}]


def test_last_screenshot_b64_uses_history_api():
    hist = MagicMock()
    hist.screenshots = MagicMock(return_value=[None, "YmF0aXM="])
    assert last_screenshot_b64(hist) == "YmF0aXM="

    hist.screenshots = MagicMock(return_value=[])
    assert last_screenshot_b64(hist) is None


def test_progress_output_from_last_history():
    mo = MagicMock()
    mo.memory = "mem"
    mo.next_goal = "goal"
    last = MagicMock()
    last.model_output = mo
    hist = MagicMock()
    hist.history = [last]
    assert progress_output(hist) == "mem\ngoal"


def test_progress_output_empty():
    assert progress_output(None) is None
    assert progress_output(MagicMock(history=[])) is None


@pytest.mark.parametrize(
    ("limit", "expected_len"),
    [
        (1, 1),
        (3, 3),
        (100, 4),
    ],
)
def test_history_to_steps_limit_boundaries(limit, expected_len):
    items = [_history_item(memory=str(i)) for i in range(4)]
    hist = MagicMock()
    hist.history = items
    out = history_to_steps(hist, limit)
    assert len(out) == expected_len


# --- SessionRegistry.snapshot ---


def _done_history(*, with_b64: str | None = "aGVsbG8="):
    hist = MagicMock()
    hist.history = []
    hist.is_done = MagicMock(return_value=True)
    hist.is_successful = MagicMock(return_value=True)
    hist.final_result = MagicMock(return_value="Task complete.")
    hist.screenshots = MagicMock(
        return_value=[with_b64] if with_b64 else [],
    )
    return hist


def _fake_session(**kwargs) -> BrowserMcpSession:
    browser = MagicMock()
    browser.kill = MagicMock(return_value=None)
    return BrowserMcpSession(
        id="test-session-id",
        browser_session=browser,
        live_url="ws://test",
        **kwargs,
    )


@pytest.mark.asyncio
async def test_snapshot_omit_steps():
    reg = SessionRegistry()
    state = _fake_session()
    state.last_history = _done_history()
    state.finished_at = "2025-01-01T00:00:00Z"

    body = await reg.snapshot(state, include_screenshot=False, include_steps_raw=None)
    assert "steps" not in body
    assert body["status"] == "finished"


@pytest.mark.asyncio
async def test_snapshot_include_steps_zero_means_no_steps_key():
    reg = SessionRegistry()
    state = _fake_session()
    state.last_history = _done_history()
    state.finished_at = "2025-01-01T00:00:00Z"

    body = await reg.snapshot(state, include_screenshot=False, include_steps_raw=0)
    assert "steps" not in body


@pytest.mark.asyncio
async def test_snapshot_include_steps_adds_steps():
    reg = SessionRegistry()
    state = _fake_session()
    item = MagicMock()
    st = MagicMock()
    st.url = "https://x.example/"
    st.screenshot_path = None
    item.state = st
    mo = MagicMock()
    mo.memory = "m"
    mo.evaluation_previous_goal = "e"
    mo.next_goal = "n"
    mo.action = None
    item.model_output = mo
    hist = MagicMock()
    hist.history = [item]
    hist.is_done = MagicMock(return_value=True)
    hist.is_successful = MagicMock(return_value=True)
    hist.final_result = MagicMock(return_value="ok")
    hist.screenshots = MagicMock(return_value=[])

    state.last_history = hist
    state.finished_at = "2025-01-01T00:00:00Z"

    body = await reg.snapshot(state, include_screenshot=False, include_steps_raw=-1)
    assert "steps" in body
    assert len(body["steps"]) == 1
    assert body["steps"][0]["number"] == 1
    assert body["steps"][0]["url"] == "https://x.example/"


@pytest.mark.asyncio
async def test_snapshot_include_screenshot_attaches_when_present():
    reg = SessionRegistry()
    state = _fake_session()
    state.last_history = _done_history(with_b64="aGVsbG8=")
    state.finished_at = "2025-01-01T00:00:00Z"

    body = await reg.snapshot(state, include_screenshot=True, include_steps_raw=None)
    assert body.get("screenshot") == "aGVsbG8="


@pytest.mark.asyncio
async def test_snapshot_include_screenshot_omits_when_no_shot():
    reg = SessionRegistry()
    state = _fake_session()
    state.last_history = _done_history(with_b64=None)
    hist = state.last_history
    hist.screenshots = MagicMock(return_value=[])
    state.finished_at = "2025-01-01T00:00:00Z"

    body = await reg.snapshot(state, include_screenshot=True, include_steps_raw=None)
    assert "screenshot" not in body


@pytest.mark.asyncio
async def test_snapshot_closed_raises():
    reg = SessionRegistry()
    state = _fake_session()
    state.closed = True
    with pytest.raises(RuntimeError, match="session is closed"):
        await reg.snapshot(state, include_screenshot=False, include_steps_raw=None)


@pytest.mark.asyncio
async def test_idle_loop_closes_session_after_timeout():
    reg = SessionRegistry()
    browser = MagicMock()
    browser.kill = AsyncMock()
    sid = "idle-test-sid"
    state = BrowserMcpSession(
        id=sid,
        browser_session=browser,
        live_url="ws://test",
        idle_timeout_seconds=1,
    )
    async with reg._lock:
        reg._sessions[sid] = state

    await reg._session_idle_loop(sid)

    async with reg._lock:
        assert sid not in reg._sessions
    browser.kill.assert_awaited()


@pytest.mark.asyncio
async def test_touch_idle_activity_extends_deadline_when_agent_idle():
    reg = SessionRegistry()
    state = _fake_session()
    state.idle_timeout_seconds = 60
    state.runner_task = None
    state._idle_deadline = 0.0
    reg.touch_idle_activity(state)
    assert state._idle_deadline is not None and state._idle_deadline > 0.0


@pytest.mark.asyncio
async def test_touch_idle_activity_noop_while_running():
    reg = SessionRegistry()
    state = _fake_session()
    state.idle_timeout_seconds = 60
    t = MagicMock()
    t.done = MagicMock(return_value=False)
    state.runner_task = t
    state._idle_deadline = 123.0
    reg.touch_idle_activity(state)
    assert state._idle_deadline == 123.0
