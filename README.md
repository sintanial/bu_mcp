# browser-mcp

MCP server on top of [browser-use](https://github.com/browser-use/browser-use): long-lived browser sessions, status polling, and follow-up tasks without starting from scratch each time.

---

## Purpose

This repo targets **agents** (LLM + MCP): start a session once, then **drive it** with tools — `session_status`, optionally **`session_supplement`** (user input, OTP, clarifications), then **`session_close`**. This is not a one-shot screenshot flow; it is full automation with a **live browser context**.

In short: **session = `session_id`**; the agent only calls tools and reads responses.

---

## Tools

| Tool | Role |
|------|------|
| `session_start` | Start + task → `session_id`, `live_url`. Optional **`bu_profile_id`** (cloud profile) → session runs in the cloud and a **Browser Use API key is required**; without `bu_profile_id` → local headless browser with a **persistent profile** (`~/.browser-mcp/local-profile` or `BROWSER_MCP_LOCAL_USER_DATA_DIR`) |
| `session_status` | Poll: status, output, steps, screenshot per flags |
| `session_supplement` | Same session + new task text (user data, etc.) |
| `session_close` | End the session when work is done |

Full contract: [`docs/mcp-spec.md`](docs/mcp-spec.md).

---

## Requirements

- **Python 3.11+**
- **LLM** key: OpenAI and/or Anthropic (via env, HTTP headers, or `params._meta` on `tools/call` — see below)
- For **cloud** (`session_start` with **`bu_profile_id`**): Browser Use key — `BROWSER_USE_API_KEY` or header / `_meta` (required when using cloud)

---

## Installation

1. Clone the repository and `cd` into the project directory.

2. Create a virtual environment and install the package in editable mode:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install -e .
   ```

3. Confirm **`browser-mcp`** is on your `PATH` (typically `.venv/bin/browser-mcp`).

Dependencies are listed in [`pyproject.toml`](pyproject.toml): `browser-use`, `mcp`, `httpx`, `pydantic`.

---

## Running

The server uses **stdio** (JSON-RPC MCP): the **client** (IDE, gateway) spawns the process — not a standalone HTTP port for the usual setup.

For a quick local check from a shell, set env vars and run the entrypoint:

```bash
source .venv/bin/activate
export OPENAI_API_KEY=...
# when using cloud + bu_profile_id:
# export BROWSER_USE_API_KEY=...

browser-mcp
```

Equivalent:

```bash
python -m browser_mcp
```

In production, set the **full path** to `browser-mcp` from your venv in the MCP client settings.

---

## Secrets and keys

**Keys are never passed as tool arguments.** Resolution order: HTTP headers (streamable MCP) → **`params._meta`** on each `tools/call` (stdio) → process environment variables.

| Environment variable | Purpose |
|----------------------|---------|
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Agent LLM (if no headers / `_meta`) |
| `BROWSER_USE_API_KEY` | Required for cloud when **`bu_profile_id`** is set (if no header / `_meta`) |
| `BROWSER_MCP_LOCAL_USER_DATA_DIR` | Chromium profile directory for **local** mode (no `bu_profile_id`); default `~/.browser-mcp/local-profile` |

Headers and `_meta` field names are summarized in **`initialize.instructions`** and the MCP resource **`browser-mcp://authentication`**. Details: [`docs/mcp-spec.md`](docs/mcp-spec.md) (secrets section).

---

## IDE setup

### Cursor / Claude Desktop

Add an MCP server of type **stdio**: command = path to `browser-mcp` in your venv, no arguments; set `env` with keys if needed.

---

## OpenClaw and agents

This repo also targets **OpenClaw** and other **agent** hosts: the agent gets the tool set and runs the flow — `session_start` (optionally with **`bu_profile_id`** for cloud) → `session_status` loop → optionally `session_supplement` → `session_close`.

Bundled OpenClaw skill:

- **`skills/browser-use-mcp/SKILL.md`** (OpenClaw skill id: **`browser_use_mcp`**) — install, env, stdio, auth, tool call order.

To load the skill:

1. Copy **`skills/browser-use-mcp`** to **`~/.openclaw/skills/browser-use-mcp`**, **or**
2. Add this repository’s `skills` directory to **`skills.load.extraDirs`** in `openclaw.json`.

Then restart the gateway or start a new session (`/new`). Optionally run `openclaw skills list`.

---

## Documentation

| File | Contents |
|------|----------|
| [`docs/mcp-spec.md`](docs/mcp-spec.md) | Tool contract, fields, flows |
| [`skills/browser-use-mcp/SKILL.md`](skills/browser-use-mcp/SKILL.md) | OpenClaw skill **`browser_use_mcp`** |

### Package layout (`browser_mcp`)

| Module | Role |
|--------|------|
| [`constants.py`](browser_mcp/constants.py) | Public Browser Use cloud base URL (not secrets) |
| [`auth_keys.py`](browser_mcp/auth_keys.py) | Key resolution: HTTP / `_meta` / env |
| [`instructions.py`](browser_mcp/instructions.py) | `initialize.instructions` and auth resource text |
| [`cloud/`](browser_mcp/cloud/) | Cloud API: create/stop remote browser |
| [`local_profile.py`](browser_mcp/local_profile.py) | Local Chromium profile directory (no `bu_profile_id`) |
| [`tool_definitions.py`](browser_mcp/tool_definitions.py) | MCP tool descriptors |
| [`tool_handlers.py`](browser_mcp/tool_handlers.py) | `tools/call` logic |
| [`sessions.py`](browser_mcp/sessions.py) | browser-use sessions, registry, status snapshot |
| [`llm_factory.py`](browser_mcp/llm_factory.py) | LLM setup for the agent |
| [`server.py`](browser_mcp/server.py) | MCP registration (tools, resources), stdio |

### Security

There are **no** hard-coded API keys in the repository — only environment variable names and the public base URL `https://api.browser-use.com`. Keys go through env, HTTP headers, or `params._meta`. `.env` is in `.gitignore`; do not commit secrets to git.
