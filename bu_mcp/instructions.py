"""MCP initialize instructions and auth resource (markdown)."""

from __future__ import annotations

AUTH_RESOURCE_URI = "bu-mcp://authentication"

MCP_SERVER_INSTRUCTIONS = """bu_mcp: session_start, session_status, session_supplement, session_close.

Secrets are NOT tool arguments. Priority: HTTP headers X-OpenAI-Api-Key / X-Anthropic-Api-Key / X-Browser-Use-Api-Key, then tools/call params._meta (x-openai-api-key, etc.), then env OPENAI_API_KEY, ANTHROPIC_API_KEY, BROWSER_USE_API_KEY on the server process.

Cloud (bu_profile_id set): Browser Use API key required. Local (no bu_profile_id): persistent profile on disk (default ~/.bu_mcp/local-profile); OpenAI or Anthropic required for the agent.
Same text: resource bu-mcp://authentication."""
