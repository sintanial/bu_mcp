# bu_mcp

MCP server on top of [browser-use](https://github.com/browser-use/browser-use): long-lived browser sessions, status polling, and follow-up tasks (`session_supplement`) without starting from scratch each time.

**Agents:** read **`AGENTS.md`** first, then **`TOOLS.md`** for the full tool contract.

---

## Tools

| Tool | Role |
|------|------|
| `session_start` | Start + task → `session_id`, `live_url`. Optional **`bu_profile_id`** (cloud) → Browser Use API key required; without it → local headless Chromium with persistent profile (`~/.bu_mcp/local-profile` or `BU_MCP_LOCAL_USER_DATA_DIR`) |
| `session_status` | Poll: status, output, optional steps / screenshot |
| `session_supplement` | Same session + new task text |
| `session_close` | End the session when work is done |

---

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

CLI: **`bu-mcp`**. Module: **`python -m bu_mcp`**.

Dev tests: `pip install -e ".[dev]"` then `pytest tests/`.

Manual E2E (local + optional cloud): `python tests/e2e_local_cloud.py --help` (requires keys in env).

---

## Run

Streamable HTTP MCP — default **`http://127.0.0.1:8765/mcp`**.

| Variable | Default | Meaning |
|----------|---------|---------|
| `BU_MCP_HOST` | `127.0.0.1` | Bind (`0.0.0.0` in Docker) |
| `BU_MCP_PORT` | `8765` | Port |
| `BU_MCP_HTTP_PATH` | `/mcp` | Path |
| `BU_MCP_LOG_LEVEL` | `info` | Uvicorn log level |
| `BU_MCP_STATELESS_HTTP` | off | Stateless MCP transport |
| `BU_MCP_JSON_RESPONSE` | off | JSON instead of SSE |
| `BU_MCP_LOCAL_USER_DATA_DIR` | `~/.bu_mcp/local-profile` | Local Chromium profile |
| `BU_MCP_DEFAULT_MAX_STEPS` | `100` | Default step cap (max 500) |

Secrets: **`OPENAI_API_KEY`** / **`ANTHROPIC_API_KEY`** / **`BROWSER_USE_API_KEY`** (cloud), or HTTP headers / `tools/call` `_meta` — see **`TOOLS.md`**.

---

## Docker

```bash
cp .env.example .env   # optional
docker compose build
docker compose up -d bu-mcp
```

MCP URL from host: **`http://127.0.0.1:8765/mcp`**. Volume **`bu_mcp_profile`** → **`/data/bu-mcp-profile`**.

---

## Documentation (root)

| File | Contents |
|------|----------|
| [`AGENTS.md`](AGENTS.md) | Short rules and flow for coding agents |
| [`TOOLS.md`](TOOLS.md) | Normative MCP tool definitions for this server |
| [`SKILL.md`](SKILL.md) | Optional OpenClaw skill id **`bu_mcp`** (copy to `~/.openclaw/skills/bu_mcp/` or use `skills.load.extraDirs`) |

### Package layout (`bu_mcp/`)

| Module | Role |
|--------|------|
| `auth_keys.py` | Keys: HTTP / `_meta` / env |
| `instructions.py` | `initialize.instructions`, resource `bu-mcp://authentication` |
| `cloud/` | Browser Use Cloud HTTP |
| `local_profile.py` | Local Chromium profile dir |
| `tool_definitions.py` / `tool_handlers.py` | MCP tools |
| `sessions.py` | Session registry + browser-use agent |
| `llm_factory.py` | LLM for the agent |
| `server.py` | Streamable HTTP app |

---

## Security

No committed secrets. Use `.env` (gitignored) or your orchestrator’s secret store.
