---
name: bu_mcp
description: >-
  Run or integrate the bu_mcp MCP server (browser-use over Streamable HTTP):
  session_start, session_status, session_supplement, session_close. Use when
  wiring HTTP MCP, Docker, env keys, or the session workflow for Browser Use
  Cloud vs local Chromium.
metadata:
  openclaw:
    requires:
      bins: ["python3"]
---

# bu_mcp (browser-use MCP)

- **PyPI / install name:** `bu-mcp`
- **Python package:** `bu_mcp`
- **CLI:** `bu-mcp` · **`python -m bu_mcp`**
- **Tool contract:** **`TOOLS.md`** · **agent cheat sheet:** **`AGENTS.md`**

## Transport

**Streamable HTTP** on a TCP port (default **8765**), path **`/mcp`** → e.g. `http://127.0.0.1:8765/mcp`. Not stdio.

## Env (server process)

- **LLM:** `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` (or headers / `_meta` on each `tools/call`)
- **Cloud** (`bu_profile_id` on `session_start`): `BROWSER_USE_API_KEY` (or header / `_meta`)
- **Local profile dir:** `BU_MCP_LOCAL_USER_DATA_DIR` (default `~/.bu_mcp/local-profile`)
- **HTTP:** `BU_MCP_HOST`, `BU_MCP_PORT`, `BU_MCP_HTTP_PATH`, `BU_MCP_DEFAULT_MAX_STEPS`, etc.

## Tool flow

1. `session_start` → save `session_id`, `live_url`
2. Poll `session_status` until done or blocked
3. If user input needed → `session_supplement` (same `session_id`, one `task` string)
4. When finished → `session_close`

## OpenClaw

Install this skill by copying **`SKILL.md`** to **`~/.openclaw/skills/bu_mcp/SKILL.md`** (create the `bu_mcp` folder), or add the **repository root** to **`skills.load.extraDirs`** in `openclaw.json` if your version loads `SKILL.md` from that tree. Register the MCP Streamable HTTP URL per OpenClaw docs.

## Docker

`docker compose up -d bu-mcp` from the repo root; URL from host `http://127.0.0.1:8765/mcp` unless you change `BU_MCP_PORT`.
