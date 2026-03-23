"""Short text for MCP initialize.instructions and resources/read (auth summary)."""

from __future__ import annotations

AUTH_RESOURCE_URI = "browser-mcp://authentication"

MCP_SERVER_INSTRUCTIONS = """browser-mcp: session_start, session_status, session_supplement, session_close.

No API keys in tool args. Priority: HTTP headers → tools/call params._meta → env.
Headers: X-Browser-Use-API-Key (required if session_start sets bu_profile_id for cloud), X-OpenAI-Api-Key, X-Anthropic-Api-Key. Stdio _meta: x-browser-use-api-key, x-openai-api-key, x-anthropic-api-key.
Env: BROWSER_USE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY.
Cloud (bu_profile_id set): Browser Use API key required. Local (no bu_profile_id): persistent profile on disk (default ~/.browser-mcp/local-profile); OpenAI or Anthropic required for the agent.
Same text: resource browser-mcp://authentication."""
