# bu_mcp — tools (v1)

Normative contract for MCP **tools** on the **bu_mcp** Streamable HTTP server (browser-use under the hood). For agent-oriented entry points see **`AGENTS.md`**.

There is **no** tool to list cloud profiles — pass the cloud profile id only in **`session_start`** as **`bu_profile_id`** when cloud is needed.

## General rules

1. **Session id** — all live automation uses only **`session_id`**. There are no separate `run_id`, split `create` + `start`, or `continue` / `cancel` tools.

2. **Browser mode (`session_start`)** — optional **`bu_profile_id`**:
   - **Set** — session runs on **Browser Use Cloud** with that profile; a **Browser Use API key** is required (header / `_meta` / `BROWSER_USE_API_KEY`); start fails without it.
   - **Omitted** — **local** (headless) browser with a **persistent on-disk profile** (default `~/.bu_mcp/local-profile`, or **`BU_MCP_LOCAL_USER_DATA_DIR`**).

3. **Secrets (not in tool arguments)** — LLM and Browser Use keys are **not** passed as tool fields. Use:
   - **HTTP (streamable MCP):** request headers:
     - `X-Browser-Use-API-Key` — required when **`bu_profile_id`** is set (cloud);
     - `X-OpenAI-Api-Key` / `X-Anthropic-Api-Key` — agent models.
   - **Optional:** the same values in **`_meta`** on **`tools/call` `params`** (lowercase hyphenated names: `x-browser-use-api-key`, `x-openai-api-key`, `x-anthropic-api-key`).
   - **Fallback:** environment variables `BROWSER_USE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` on the MCP process.

   Priority: HTTP headers → `_meta` → env.

   **Short copy for MCP clients:** `initialize.instructions` and resource **`bu-mcp://authentication`** (`resources/read`).

4. **`live_url`** — required on successful **`session_start`** and **`session_supplement`**. For a closed or missing session — error or implementation-defined contract.

5. **MCP response format** — one consistent format (e.g. JSON in `CallToolResult` text) so clients parse predictably.

### Field `session_id`

**Meaning:** opaque id for **one** long-lived browser session on the server: shared context (tabs, cookies), chain `session_start` → repeated `session_status` and `session_supplement` as needed → `session_close`. String format is implementation-defined; clients do not parse or construct it.

**Where to get it:** returned by successful **`session_start`** (and echoed by **`session_supplement`**); the same literal is passed to all later calls for that session.

**`description` for MCP `inputSchema.properties.session_id` (same for `session_status`, `session_supplement`, `session_close`):**

> Opaque session identifier returned by `session_start` (echoed again by `session_supplement`). Use the exact same value on every `session_status`, `session_supplement`, and `session_close` call for this browser session until it is closed.

**`description` for `session_start` / `session_supplement` response (`session_id` in JSON):**

> Identifier of this browser session; pass unchanged on all later `session_status`, `session_supplement`, and `session_close` calls until the session is closed.

---

## 1. `session_start`

**Purpose:** create a working session (locally with persistent on-disk profile **or** in cloud via **`bu_profile_id`**) and run the agent on `task`.

**`description` (for MCP tool descriptor):**

> Start a browser automation session and run the agent task (browser-use under the hood: full browser context, multi-step execution). If `bu_profile_id` is set, use Browser Use Cloud with that profile and require `X-Browser-Use-API-Key`. If omitted, run locally with a persistent on-disk profile. Response includes `session_id` and `live_url` — poll `session_status` with that `session_id` to track progress; use `session_supplement` when `output` (or `steps`) shows that user input is needed.

**Input:**

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `task` | string | yes | Goal for the agent. |
| `max_steps` | integer | no | Max agent steps; default from **`BU_MCP_DEFAULT_MAX_STEPS`** (default 100), max 500. |
| `bu_profile_id` | string (UUID) | no | Browser Use **cloud** profile. If set — **cloud only**, Browser Use key **required**. If omitted — **local** browser with local profile. |
| `country_code` | string | no | Country code (e.g. `RU`, `DE`) for locale/proxy in cloud. |
| `idle_timeout_seconds` | integer | no | After the **agent stops**, auto-close the browser session if no **`session_status`** or **`session_supplement`** arrives for this many seconds. Default **900** (15 minutes); override per start. While the agent is **running**, the idle timer does not count down. Default for the server process: **`BU_MCP_DEFAULT_IDLE_TIMEOUT_SECONDS`** (falls back to **900**). |

LLM and Browser Use keys are not tool arguments — see **§3** above.

**Output (success),** JSON — **required fields:**

| Field | Description |
|------|-------------|
| `session_id` | Id of **this** session; keep and pass the same `session_id` on all later tool calls until closed. |
| `live_url` | Live view URL for the session. |

**Errors:** missing `session_id` or inconsistent `live_url`; if **`bu_profile_id`** is set but no Browser Use key — error with a clear message.

---

## 2. `session_status`

**Purpose:** poll session state.

**`description` (for MCP tool descriptor):**

> Poll a browser session by `session_id`. Returns a fixed snapshot: `status`, `output`, `finished_at`, `is_success`. Structured fields like “waiting for phone” are not provided — infer what the agent needs from `output` (and from `steps` if you requested them). Optional request flags: `include_screenshot`; `include_steps` — omit or `0` for no steps, `-1` for full history, `N>0` for the last N steps (returned as `steps` in the response).
>
> Poll every few seconds while the task is in progress (`status` / `output` tell you when it is done or stuck). If `output` implies missing user data, call `session_supplement` with the same `session_id` and a `task` string (e.g. phone number, OTP, or follow-up instruction). When `session_status` shows the agent considers the overall task **fully finished** (per `status`, `output`, `finished_at`, `is_success`), stop polling and call `session_close` for that `session_id`. Do not call `session_close` if more user input or follow-up work may still be needed. If unsure, poll `session_status` once more before closing. After each call, briefly summarize progress for the user in plain language — not raw JSON only.

**Input:**

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `session_id` | string | yes | Same `session_id` as returned by `session_start` / `session_supplement` for this work. |
| `include_screenshot` | boolean | no | If `true`, include **`screenshot`** (format is implementation-defined). |
| `include_steps` | integer | no | Agent steps as **`steps`**: **omitted or `0`** — omit; **`-1`** — all steps; **`> 0`** — at most the last **N** steps. |

**Output (success),** JSON — **fixed fields (always):**

| Field | Description |
|------|-------------|
| `status` | Session/task status string (enum is implementation-defined). |
| `output` | Final or intermediate agent text; may be `null` or empty while running — per implementation. |
| `finished_at` | ISO 8601 completion time or `null` if not finished. |
| `is_success` | `true` / `false` / `null` — success from agent/service; details in `output`. |

**Optional (on request):**

| Field | Condition |
|------|----------|
| `steps` | If `include_steps` is `-1` or `> 0` — step array (structure is implementation-defined). |
| `screenshot` | If `include_screenshot === true`. |

**Missing or already closed session:** preferably a **tool error**.

---

## 3. `session_supplement`

**Purpose:** continue in the **same** session with a new **`task`** (phone, SMS code, clarification, site prompt, etc.) without a new `session_start`.

**`description` (for MCP tool descriptor):**

> Continue an existing browser session with a new natural-language `task`. Use after `session_status` shows the agent needs more input — embed facts (phone, OTP, credentials text the user provided) or follow-up instructions in the `task` string; the same `session_id` and browser context are reused (browser-use under the hood). Response shape matches `session_start`: `session_id` and `live_url`. Then poll `session_status` again until the work completes or needs another supplement.

**Input:**

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `session_id` | string | yes | Session to continue — **same** `session_id` as at start (do not create a new one). |
| `task` | string | yes | What to do next or what data to apply; single string for the agent. |

**Output (success),** JSON — **same as `session_start`**, required fields:

| Field | Description |
|------|-------------|
| `session_id` | Confirms session: **same** id as in the request (and originally from `session_start`). |
| `live_url` | Live view URL for this session. |

**Errors:** session not found or closed; response without consistent `session_id` / `live_url`.

---

## 4. `session_close`

**Purpose:** end the **logical** task session after `session_status` shows the agent has **fully** completed the work (goal reached, nothing left to do).

**`description` (for MCP tool descriptor):**

> End the automation session after the agent has **fully completed** the task. Use this only when `session_status` indicates the work is done from the agent’s perspective (`status`, `output`, `finished_at`, `is_success` — no further steps or user input expected). Do **not** call this while the agent may still need another `session_supplement`, or if the user might assign follow-up work in the same session. If you are unsure, poll `session_status` once more before closing.

**Input:**

| Field | Type | Required | Description |
|------|------|----------|-------------|
| `session_id` | string | yes | Task session the agent finished; same `session_id` as for this `session_start` / `session_supplement` chain. |

**Output (success):** e.g. `{ "closed": true }`.

**Errors:** unknown or already ended `session_id` — report as error or idempotent success (pick one for v1).

---

## Tool list summary (v1)

| # | Name | Role |
|---|------|------|
| 1 | `session_start` | Start session + task → **`session_id`**, **`live_url`** (local or cloud via `bu_profile_id`). |
| 2 | `session_status` | Monitor → `status`, `output`, `finished_at`, `is_success`; optional `steps`, `screenshot`. |
| 3 | `session_supplement` | Same session + new `task` → **`session_id`**, **`live_url`** (like `session_start`). |
| 4 | `session_close` | Close session when the agent has **fully** completed the task (per `session_status`). |

---

## Typical agent flow

1. `session_start` (optionally with **`bu_profile_id`** for cloud and required Browser Use key) → save `session_id`, `live_url`.
2. Loop `session_status` until completion by `status` / `output` / `finished_at`.
3. If `output` (and optionally `steps`) show missing user data → `session_supplement` with the same `session_id` and **`task`**.
4. When `session_status` shows the agent has **fully** finished → `session_close` with the same `session_id`.

---

## Server configuration (environment)

| Variable | Role |
|----------|------|
| `BU_MCP_HOST` / `BU_MCP_PORT` / `BU_MCP_HTTP_PATH` | HTTP bind and MCP path (default `/mcp`). |
| `BU_MCP_LOCAL_USER_DATA_DIR` | Local Chromium profile directory. |
| `BU_MCP_DEFAULT_MAX_STEPS` | Default `max_steps` cap helper (1–500). |
| `BU_MCP_LOG_LEVEL` | Uvicorn log level. |
| `BU_MCP_STATELESS_HTTP` / `BU_MCP_JSON_RESPONSE` | MCP Streamable HTTP transport toggles. |
