# Agent notes — bu_mcp

Use this file when working in **this repository** or when driving the **bu_mcp** MCP server.

## Canonical reference

- **`TOOLS.md`** — normative MCP tool definitions for this server (arguments, responses, secrets, env).
- **`README.md`** — install, run, Docker, quick links.

## Hard rules

1. **Never put API keys inside tool arguments.** Keys go in HTTP headers, `tools/call` `params._meta`, or the server process environment (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `BROWSER_USE_API_KEY`). See `TOOLS.md` §3.
2. **One session id per job:** reuse the same `session_id` for `session_status`, `session_supplement`, and `session_close` until the session is explicitly closed.
3. **Cloud vs local:** if `session_start` includes `bu_profile_id`, a Browser Use API key is mandatory; without `bu_profile_id`, the server uses local headless Chromium with a persistent profile (`~/.bu_mcp/local-profile` by default).

## Tool order (happy path)

1. `session_start` → keep `session_id` and `live_url`.
2. Poll `session_status` until the task is done or blocked.
3. If the agent needs user data → `session_supplement` with the same `session_id` and a single natural-language `task` string.
4. When `session_status` shows the work is fully complete → `session_close`.

## MCP surface

- **Transport:** Streamable HTTP (not stdio). Default URL: `http://127.0.0.1:8765/mcp` if defaults unchanged.
- **Server id (MCP):** `bu_mcp`.
- **Auth resource URI:** `bu-mcp://authentication` (same summary as `initialize.instructions`).

## Python package layout

- Import package: **`bu_mcp`**
- CLI: **`bu-mcp`**
- Module entry: `python -m bu_mcp`

## Optional skill (OpenClaw / shared skills dirs)

- **`SKILL.md`** (repo root) — same content; skill id **`bu_mcp`**. For OpenClaw, copy to `~/.openclaw/skills/bu_mcp/SKILL.md` or point `skills.load.extraDirs` at this repo root.
