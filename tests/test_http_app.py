"""Smoke tests for Streamable HTTP Starlette app factory."""

from __future__ import annotations

import pytest
from starlette.routing import Route

from bu_mcp.server import build_mcp_server, build_streamable_http_app


def test_build_mcp_server_has_version_and_instructions():
    s = build_mcp_server()
    assert s.name == "bu_mcp"
    assert s.version
    assert s.instructions and "session_start" in s.instructions


def test_build_streamable_http_app_has_mcp_route(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BU_MCP_HTTP_PATH", "/mcp")
    app = build_streamable_http_app()
    routes = [r for r in app.routes if isinstance(r, Route)]
    assert routes
    assert any(getattr(r, "path", None) == "/mcp" for r in routes)
