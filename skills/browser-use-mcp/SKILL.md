---
name: browser_use_mcp
description: >-
  Installs, configures, and operates the browser-mcp stdio MCP server (browser-use:
  session_start, session_status, session_supplement, session_close).
  Use when the user wants browser automation via MCP, OpenClaw or IDE integration,
  to run or wire browser-mcp, set keys for Browser Use Cloud or LLM, or follow
  the session workflow. Distinguishes this stack from generic “browser-use” CLI.
metadata:
  openclaw:
    requires:
      bins: ["python3"]
---

# browser-use MCP (`browser-mcp` package)

Skill id **`browser_use_mcp`** refers to this repo’s **browser-mcp** MCP server (Python package name / CLI `browser-mcp`), built on **browser-use**. It is not the browser-use project’s own MCP unless upstream ships the same binary.

## What this is

**browser-mcp** is a **stdio MCP server**: the **host** (IDE, gateway, MCP client) spawns `browser-mcp` and speaks JSON-RPC over stdin/stdout. There is no standalone HTTP port in the default setup.

There is **no** `profiles_list` tool. Cloud profile selection uses **`bu_profile_id`** on **`session_start`** only.

## Install

1. **Python ≥ 3.11** and a checkout or install of this package (repository root is often named `browser-mcp`).
2. From the repo directory:

   ```bash
   python3 -m venv .venv && . .venv/bin/activate
   pip install -e .
   ```

3. Confirm **`browser-mcp`** is on `PATH` (typically `.venv/bin/browser-mcp`).

## Run / wire the process

- Configure the MCP client with:
  - **Command:** absolute path recommended, e.g. `/path/to/repo/.venv/bin/browser-mcp`
  - **Arguments:** none
  - **Working directory:** optional (repo root is fine if the venv is local)
- **Environment** for the child process:
  - **Always** (for the agent LLM): `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` (or headers / `_meta`).
  - **When** `session_start` includes **`bu_profile_id`** (Cloud): **`BROWSER_USE_API_KEY`** (or `X-Browser-Use-API-Key` / `_meta`) is **required**.
  - **Local mode** (no `bu_profile_id`): optional **`BROWSER_MCP_LOCAL_USER_DATA_DIR`** — Chromium profile directory (default `~/.browser-mcp/local-profile`).
- **HTTP MCP:** pass secrets as headers. **stdio:** use **`tools/call` `params._meta`**.

## Auth (never in tool arguments)

1. HTTP headers: `X-Browser-Use-API-Key`, `X-OpenAI-Api-Key`, `X-Anthropic-Api-Key`
2. **`params._meta`** on each `tools/call`: `x-browser-use-api-key`, `x-openai-api-key`, `x-anthropic-api-key`
3. **Env:** `BROWSER_USE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

**Cloud:** if **`bu_profile_id`** is set in `session_start`, Browser Use API key is **mandatory**. **Local:** no Browser Use key needed; OpenAI or Anthropic still required for the agent LLM.

After connect: **`initialize.instructions`** and resource **`browser-mcp://authentication`**.

## Tools workflow

1. **`session_start`** — `task`, optional **`bu_profile_id`** (Cloud UUID), optional `country_code`, `max_steps`. Save **`session_id`**, **`live_url`**.
2. **`session_status`** — poll; optional `include_screenshot`, `include_steps`.
3. **`session_supplement`** — same `session_id`, new `task` if user input is needed.
4. **`session_close`** — when the task is fully finished.

## Load this skill in OpenClaw

- Copy **`skills/browser-use-mcp`** to **`~/.openclaw/skills/browser-use-mcp`**, or add this repo’s **`skills`** directory via **`skills.load.extraDirs`** in `openclaw.json`.
- Restart the gateway or start a new session (`/new`). Check **`openclaw skills list`** if available.

## Troubleshooting

- **Command not found:** use the full path to `.venv/bin/browser-mcp`.
- **Cloud errors with `bu_profile_id`:** set `BROWSER_USE_API_KEY` (or header / `_meta`).
- **LLM errors:** set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (or header / `_meta`).
- Contract: **`docs/mcp-spec.md`**.
