"""Long-lived browser sessions backed by browser-use BrowserSession + Agent."""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from browser_use import Agent, BrowserSession
from browser_use.agent.views import AgentHistoryList
from browser_use.browser.cloud.views import CreateBrowserRequest

from bu_mcp.cloud import create_browser as cloud_create_browser, stop_browser as cloud_stop_browser
from bu_mcp.llm_factory import build_llm
from bu_mcp.local_profile import resolve_local_user_data_dir


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_browser_use_key(explicit: str | None) -> str | None:
    v = (explicit or "").strip()
    return v or os.getenv("BROWSER_USE_API_KEY")


def _normalize_bu_profile_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _prepare_task(task: str, country_code: str | None) -> str:
    if not country_code:
        return task
    return f"[Country/locale context: {country_code.strip()}]\n{task}"


def _normalize_proxy_country(country_code: str | None) -> str | None:
    if not country_code:
        return None
    c = country_code.strip().lower()
    return c or None


def clamp_max_steps(raw: int | None) -> int:
    default = int(os.getenv("BU_MCP_DEFAULT_MAX_STEPS", "100"))
    v = default if raw is None else int(raw)
    return max(1, min(v, 500))


def progress_output(history: AgentHistoryList | None) -> str | None:
    if not history or not history.history:
        return None
    last = history.history[-1]
    if last.model_output:
        parts = [p for p in (last.model_output.memory, last.model_output.next_goal) if p]
        if parts:
            return "\n".join(parts)
    return None


def history_to_steps(history: AgentHistoryList | None, include_limit: int | None) -> list[dict[str, Any]]:
    if not history or not history.history:
        return []
    out: list[dict[str, Any]] = []
    for i, h in enumerate(history.history):
        item: dict[str, Any] = {"number": i + 1}
        st = h.state
        if st is not None:
            if getattr(st, "url", None) is not None:
                item["url"] = st.url
            sp = getattr(st, "screenshot_path", None)
            if sp:
                item["screenshot_path"] = sp
        mo = h.model_output
        if mo is not None:
            item["memory"] = mo.memory
            item["evaluation_previous_goal"] = mo.evaluation_previous_goal
            item["next_goal"] = mo.next_goal
            if mo.action:
                item["actions"] = [a.model_dump(exclude_none=True, mode="json") for a in mo.action]
        out.append(item)
    if include_limit is None:
        return out
    if include_limit < 0:
        return out
    return out[-include_limit:]


def last_screenshot_b64(history: AgentHistoryList | None) -> str | None:
    if not history:
        return None
    shots = history.screenshots(n_last=1, return_none_if_not_screenshot=True)
    if not shots:
        return None
    return shots[-1]


@dataclass
class BrowserMcpSession:
    id: str
    browser_session: BrowserSession
    live_url: str
    cloud_browser_id: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    browser_use_api_key: str | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    runner_task: asyncio.Task[None] | None = None
    running_agent: Agent[Any, Any] | None = None
    last_history: AgentHistoryList | None = None
    last_error: str | None = None
    finished_at: str | None = None
    closed: bool = False

    async def run_agent(self, task: str, max_steps: int) -> None:
        agent: Agent[Any, Any] | None = None
        try:
            llm = build_llm(
                openai_api_key=self.openai_api_key,
                anthropic_api_key=self.anthropic_api_key,
            )
            agent = Agent(task=task, llm=llm, browser_session=self.browser_session)
            self.running_agent = agent
            await agent.run(max_steps=max_steps)
            self.last_history = agent.history
            self.last_error = None
            self.finished_at = _utc_now_iso()
        except asyncio.CancelledError:
            self.last_error = "cancelled"
            self.finished_at = _utc_now_iso()
            raise
        except Exception as e:
            self.last_error = str(e)
            if agent is not None:
                self.last_history = agent.history
            self.finished_at = _utc_now_iso()
        finally:
            self.running_agent = None
            self.runner_task = None

    def is_running(self) -> bool:
        return self.runner_task is not None and not self.runner_task.done()


class SessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, BrowserMcpSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        *,
        task: str,
        max_steps: int | None,
        bu_profile_id: str | None,
        country_code: str | None,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        browser_use_api_key: str | None = None,
    ) -> BrowserMcpSession:
        bu_pid = _normalize_bu_profile_id(bu_profile_id)
        bu_resolved = _resolve_browser_use_key(browser_use_api_key)

        if bu_pid and not bu_resolved:
            raise RuntimeError(
                "bu_profile_id requires a Browser Use Cloud API key: send HTTP header X-Browser-Use-API-Key "
                "(or the same key in tools/call params _meta), or set BROWSER_USE_API_KEY in the environment."
            )

        prepared = _prepare_task(task, country_code)
        ms = clamp_max_steps(max_steps)

        oa = (openai_api_key or "").strip() or None
        an = (anthropic_api_key or "").strip() or None
        bu = (browser_use_api_key or "").strip() or None

        cloud_browser_id: str | None = None
        if bu_pid:
            req = CreateBrowserRequest(
                cloud_profile_id=bu_pid,
                cloud_proxy_country_code=_normalize_proxy_country(country_code),
            )
            resp = await cloud_create_browser(bu_resolved, req)
            cloud_browser_id = resp.id
            live_url = resp.liveUrl
            browser = BrowserSession(cdp_url=resp.cdpUrl, is_local=False)
        else:
            udir = resolve_local_user_data_dir()
            udir.mkdir(parents=True, exist_ok=True)
            browser = BrowserSession(headless=True, user_data_dir=str(udir))
            await browser.start()
            live_url = browser.cdp_url or ""
            if not live_url:
                live_url = "about:blank"

        sid = str(uuid.uuid4())
        state = BrowserMcpSession(
            id=sid,
            browser_session=browser,
            live_url=live_url,
            cloud_browser_id=cloud_browser_id,
            openai_api_key=oa,
            anthropic_api_key=an,
            browser_use_api_key=bu,
        )
        async with self._lock:
            self._sessions[sid] = state

        state.runner_task = asyncio.create_task(state.run_agent(prepared, ms))
        return state

    async def get(self, session_id: str) -> BrowserMcpSession | None:
        async with self._lock:
            return self._sessions.get(session_id)

    async def remove(self, session_id: str) -> BrowserMcpSession | None:
        async with self._lock:
            return self._sessions.pop(session_id, None)

    async def close_session(self, session_id: str) -> bool:
        state = await self.remove(session_id)
        if state is None:
            return False
        state.closed = True
        if state.runner_task and not state.runner_task.done():
            state.runner_task.cancel()
            try:
                await state.runner_task
            except asyncio.CancelledError:
                pass
        if state.cloud_browser_id:
            bu = _resolve_browser_use_key(state.browser_use_api_key)
            if bu:
                try:
                    await cloud_stop_browser(bu, state.cloud_browser_id)
                except Exception:
                    pass
        try:
            await state.browser_session.kill()
        except Exception:
            pass
        return True

    async def snapshot(
        self,
        state: BrowserMcpSession,
        *,
        include_screenshot: bool,
        include_steps_raw: int | None,
    ) -> dict[str, Any]:
        if state.closed:
            raise RuntimeError("session is closed")

        async with state.lock:
            history: AgentHistoryList | None = None
            if state.running_agent is not None and state.running_agent.history is not None:
                history = state.running_agent.history
            elif state.last_history is not None:
                history = state.last_history

            if state.is_running():
                status = "started"
                finished_at = None
                is_success = None
                output = progress_output(history)
            elif state.last_error == "cancelled":
                status = "stopped"
                finished_at = state.finished_at
                is_success = False
                output = state.last_error
            elif state.last_error:
                status = "failed"
                finished_at = state.finished_at
                is_success = False
                output = state.last_error
            elif history is not None and history.is_done():
                status = "finished"
                finished_at = state.finished_at
                is_success = history.is_successful()
                output = history.final_result()
            elif history is not None:
                status = "finished"
                finished_at = state.finished_at
                is_success = history.is_successful()
                output = history.final_result() or progress_output(history)
            else:
                status = "created"
                finished_at = None
                is_success = None
                output = None

            body: dict[str, Any] = {
                "status": status,
                "output": output,
                "finished_at": finished_at,
                "is_success": is_success,
            }

            if include_steps_raw is not None and include_steps_raw != 0:
                limit = None if include_steps_raw < 0 else include_steps_raw
                body["steps"] = history_to_steps(history, limit)

            if include_screenshot:
                shot = last_screenshot_b64(history)
                if shot:
                    body["screenshot"] = shot

            return body
