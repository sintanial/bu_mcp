"""MCP Tool descriptors (inputSchema, descriptions). Contract: docs/mcp-spec.md."""

from __future__ import annotations

import mcp.types as types

SESSION_ID_DESC = (
    "Opaque session identifier returned by session_start (echoed again by session_supplement). "
    "Use the exact same value on every session_status, session_supplement, and session_close call "
    "for this browser session until it is closed."
)


def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="session_start",
            description=(
                "Start a browser automation session and run the agent task (browser-use under the hood: "
                "full browser context, multi-step execution). Use this when the work actually needs "
                "interactive browsing; prefer lighter APIs, scripts, or other integrations when they are enough. "
                "If bu_profile_id is set, the browser runs on Browser Use Cloud with that cloud profile; "
                "if omitted, the browser runs locally with a persistent local profile directory on disk. "
                "Use country_code when locale or phone formats matter. Response includes session_id and live_url — "
                "poll session_status with that session_id to track progress; use session_supplement when output "
                "(or steps) shows that user input is needed. Keys are not tool args (see server instructions)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Goal for the agent."},
                    "max_steps": {"type": "integer", "description": "Max agent steps (default 100, max 500)."},
                    "bu_profile_id": {
                        "type": "string",
                        "description": (
                            "Optional. Browser Use **cloud** profile UUID. If set, session runs in the cloud and "
                            "X-Browser-Use-API-Key (or env BROWSER_USE_API_KEY) is required. If omitted, session "
                            "runs locally with a persistent local profile (see server docs / BROWSER_MCP_LOCAL_USER_DATA_DIR)."
                        ),
                    },
                    "country_code": {
                        "type": "string",
                        "description": "Optional country code (e.g. RU, DE) for locale / proxy context (cloud).",
                    },
                },
                "required": ["task"],
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="session_status",
            description=(
                "Poll a browser session by session_id. Returns status, output, finished_at, is_success. "
                "Infer what the agent needs from output (and from steps if requested). "
                "Optional: include_screenshot; include_steps — omit or 0 for no steps, -1 for full history, "
                "N>0 for the last N steps (returned as steps). Poll every few seconds while the task is in progress. "
                "If output implies missing user data, call session_supplement with the same session_id and a task "
                "string. When the agent has fully completed the work, call session_close. "
                "After each call, briefly summarize progress for the user in plain language — not raw JSON only."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": SESSION_ID_DESC},
                    "include_screenshot": {"type": "boolean", "description": "If true, include screenshot (base64)."},
                    "include_steps": {
                        "type": "integer",
                        "description": "0/omit: no steps; -1: all steps; >0: last N steps.",
                    },
                },
                "required": ["session_id"],
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="session_supplement",
            description=(
                "Continue an existing browser session with a new natural-language task. Use after session_status "
                "shows the agent needs more input — embed facts (phone, OTP, credentials) or follow-up "
                "instructions in the task string; the same session_id and browser context are reused "
                "(browser-use under the hood). Response shape matches session_start: session_id and live_url. "
                "Then poll session_status again until the work completes or needs another supplement."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": SESSION_ID_DESC},
                    "task": {"type": "string", "description": "What to do next or data to apply."},
                },
                "required": ["session_id", "task"],
                "additionalProperties": False,
            },
        ),
        types.Tool(
            name="session_close",
            description=(
                "End the automation session after the agent has fully completed the task. Use this only when "
                "session_status indicates the work is done from the agent's perspective (status, output, "
                "finished_at, is_success — no further steps or user input expected). Do not call this while the "
                "agent may still need another session_supplement. If unsure, poll session_status once more before closing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": SESSION_ID_DESC},
                },
                "required": ["session_id"],
                "additionalProperties": False,
            },
        ),
    ]
