#!/usr/bin/env python3
"""Manual E2E: local headless + cloud via handle_tool_call (same path as MCP)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import httpx

from bu_mcp.cloud.browsers import BROWSER_USE_CLOUD_API_BASE
from bu_mcp.tool_handlers import handle_tool_call
from bu_mcp.sessions import SessionRegistry


def _j(tc: list) -> dict:
    return json.loads(tc[0].text)


async def _wait_done(registry: SessionRegistry, sid: str, label: str, *, max_s: int) -> dict:
    for _ in range(max_s):
        st = _j(await handle_tool_call("session_status", {"session_id": sid}, registry=registry))
        if st.get("status") != "started":
            return st
        await asyncio.sleep(1.0)
    raise RuntimeError(f"timeout waiting for agent: {label}")


async def _verify_steps_and_screenshot_contract(
    registry: SessionRegistry,
    sid: str,
    label: str,
) -> None:
    plain = _j(await handle_tool_call("session_status", {"session_id": sid}, registry=registry))
    z = _j(
        await handle_tool_call(
            "session_status",
            {"session_id": sid, "include_steps": 0},
            registry=registry,
        )
    )
    full = _j(
        await handle_tool_call(
            "session_status",
            {"session_id": sid, "include_steps": -1},
            registry=registry,
        )
    )
    last2 = _j(
        await handle_tool_call(
            "session_status",
            {"session_id": sid, "include_steps": 2},
            registry=registry,
        )
    )
    assert "steps" not in plain, f"[{label}] omit include_steps must not add steps"
    assert "steps" not in z, f"[{label}] include_steps:0 must not add steps"
    assert "steps" in full and isinstance(full["steps"], list), full
    all_steps = full["steps"]
    assert len(all_steps) >= 1, f"[{label}] expected at least one step in history"
    nums = [s["number"] for s in all_steps]
    assert nums == list(range(1, len(nums) + 1)), f"[{label}] step numbers must be 1..n"
    if len(all_steps) >= 2:
        assert last2["steps"] == all_steps[-2:], f"[{label}] last-2 must match tail of full history"
    else:
        assert last2["steps"] == all_steps

    combo = _j(
        await handle_tool_call(
            "session_status",
            {
                "session_id": sid,
                "include_screenshot": True,
                "include_steps": 1,
            },
            registry=registry,
        )
    )
    assert "steps" in combo and "screenshot" in combo, f"[{label}] combined flags must return both"
    assert len(combo["steps"]) <= 1
    raw = combo["screenshot"]
    assert isinstance(raw, str) and len(raw) > 64, f"[{label}] screenshot must be non-trivial base64"
    print(f"[{label}] steps contract OK (full={len(all_steps)}), screenshot len={len(raw)}")


async def _run_flow(
    *,
    label: str,
    registry: SessionRegistry,
    start_args: dict,
    supplement_task: str,
    max_wait_s: int,
) -> None:
    a = _j(await handle_tool_call("session_start", start_args, registry=registry))
    assert "session_id" in a and "live_url" in a, a
    sid = a["session_id"]
    live = a["live_url"]
    print(f"[{label}] session_start -> session_id={sid[:8]}... live_url scheme={live.split(':')[0]}")

    try:
        await handle_tool_call("session_supplement", {"session_id": sid, "task": "noop"}, registry=registry)
        raise AssertionError("expected busy error")
    except ValueError as e:
        assert "busy" in str(e).lower(), e
        print(f"[{label}] supplement while busy: OK")

    st1 = await _wait_done(registry, sid, f"{label} first", max_s=max_wait_s)
    assert all(k in st1 for k in ("status", "output", "finished_at", "is_success")), st1
    print(f"[{label}] first done: status={st1.get('status')} is_success={st1.get('is_success')}")

    await _verify_steps_and_screenshot_contract(registry, sid, label)

    sup = _j(
        await handle_tool_call(
            "session_supplement",
            {"session_id": sid, "task": supplement_task},
            registry=registry,
        )
    )
    assert sup.get("session_id") == sid and "live_url" in sup
    print(f"[{label}] session_supplement OK")

    st2 = await _wait_done(registry, sid, f"{label} second", max_s=max_wait_s)
    print(f"[{label}] second done: status={st2.get('status')} is_success={st2.get('is_success')}")

    clo = _j(await handle_tool_call("session_close", {"session_id": sid}, registry=registry))
    assert clo.get("closed") is True, clo
    print(f"[{label}] session_close OK")

    try:
        await handle_tool_call("session_status", {"session_id": sid}, registry=registry)
        raise AssertionError("expected error after close")
    except ValueError:
        print(f"[{label}] status after close: OK")

    print(f"[{label}] --- PASSED ---")


async def _fetch_first_cloud_profile_id() -> tuple[str | None, str | None]:
    bu_key = (os.getenv("BROWSER_USE_API_KEY") or "").strip()
    if not bu_key:
        return None, None
    url = f"{BROWSER_USE_CLOUD_API_BASE}/api/v2/profiles"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers={"X-Browser-Use-API-Key": bu_key})
    if response.status_code != 200:
        return None, None
    data = response.json()
    items = data.get("items") or []
    if not items:
        return None, None
    first = items[0]
    pid = first.get("id")
    name = first.get("name")
    if not pid:
        return None, None
    return str(pid), str(name) if name is not None else None


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--local-only", action="store_true")
    p.add_argument("--cloud-only", action="store_true")
    p.add_argument("--max-wait", type=int, default=420, help="seconds per wait phase")
    args = p.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is required", file=sys.stderr)
        return 1

    os.environ.setdefault("BROWSER_USE_SETUP_LOGGING", "false")

    task1 = "Open https://example.com and say DONE when the page title is visible."
    task2_local = "Scroll slightly then say DONE."
    task2_cloud = "Open https://example.com in a new tab if needed, then say DONE."

    run_local = not args.cloud_only
    run_cloud = not args.local_only

    if run_local:
        reg = SessionRegistry()
        await _run_flow(
            label="local",
            registry=reg,
            start_args={"task": task1, "max_steps": 8},
            supplement_task=task2_local,
            max_wait_s=args.max_wait,
        )

    if run_cloud:
        bu_key = (os.getenv("BROWSER_USE_API_KEY") or "").strip()
        prof = (
            os.getenv("BU_MCP_TEST_BU_PROFILE_ID")
            or os.getenv("BROWSER_USE_CLOUD_PROFILE_ID")
            or ""
        ).strip()
        if not bu_key:
            print("CLOUD SKIP: BROWSER_USE_API_KEY not set")
            return 0 if run_local else 1
        if not prof:
            auto_id, auto_name = await _fetch_first_cloud_profile_id()
            if auto_id:
                prof = auto_id
                label = auto_name or "(unnamed)"
                print(f"CLOUD: using first profile from API: {label!r} id={prof[:8]}...")
            else:
                print(
                    "CLOUD SKIP: no profiles from /api/v2/profiles and no "
                    "BU_MCP_TEST_BU_PROFILE_ID / BROWSER_USE_CLOUD_PROFILE_ID."
                )
                return 0 if run_local else 1

        reg_c = SessionRegistry()
        await _run_flow(
            label="cloud",
            registry=reg_c,
            start_args={
                "task": task1,
                "max_steps": 8,
                "bu_profile_id": prof,
            },
            supplement_task=task2_cloud,
            max_wait_s=args.max_wait,
        )

    print("ALL REQUESTED TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
