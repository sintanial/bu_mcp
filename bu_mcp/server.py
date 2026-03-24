"""MCP server: tools, resources, Streamable HTTP transport."""

from __future__ import annotations

import os
from collections.abc import Iterable
from contextlib import asynccontextmanager

import mcp.types as types
from mcp.server import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from bu_mcp import __version__
from bu_mcp.instructions import AUTH_RESOURCE_URI, MCP_SERVER_INSTRUCTIONS
from bu_mcp.sessions import SessionRegistry
from bu_mcp.tool_definitions import list_tools
from bu_mcp.tool_handlers import handle_tool_call

_registry = SessionRegistry()


def build_mcp_server() -> Server:
    server = Server(
        "bu_mcp",
        version=__version__,
        instructions=MCP_SERVER_INSTRUCTIONS,
    )

    @server.list_resources()
    async def _list_resources() -> list[types.Resource]:
        return [
            types.Resource(
                uri=AnyUrl(AUTH_RESOURCE_URI),
                name="authentication",
                title="Authentication & API keys",
                description="Short auth/key resolution (same as initialize.instructions).",
                mimeType="text/markdown",
            )
        ]

    @server.read_resource()
    async def _read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        if str(uri) != AUTH_RESOURCE_URI:
            raise ValueError(f"unknown resource URI: {uri}")
        return [ReadResourceContents(content=MCP_SERVER_INSTRUCTIONS, mime_type="text/markdown")]

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return list_tools()

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, object]) -> list[types.TextContent]:
        return await handle_tool_call(name, arguments, registry=_registry)

    return server


class _StreamableHTTPASGIApp:
    """ASGI app that delegates to StreamableHTTPSessionManager (same pattern as mcp FastMCP)."""

    def __init__(self, session_manager: StreamableHTTPSessionManager) -> None:
        self.session_manager = session_manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.session_manager.handle_request(scope, receive, send)


def _transport_security_for_bind_host(host: str) -> TransportSecuritySettings | None:
    h = host.strip()
    if h in ("127.0.0.1", "localhost", "::1"):
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"],
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"],
        )
    return None


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def build_streamable_http_app() -> Starlette:
    """Starlette app: MCP Streamable HTTP at `BU_MCP_HTTP_PATH` (default `/mcp`)."""
    mcp_server = build_mcp_server()
    bind_host = os.environ.get("BU_MCP_HOST", "127.0.0.1")
    stateless = _env_bool("BU_MCP_STATELESS_HTTP", default=False)
    json_response = _env_bool("BU_MCP_JSON_RESPONSE", default=False)
    path = os.environ.get("BU_MCP_HTTP_PATH", "/mcp").strip() or "/mcp"
    if not path.startswith("/"):
        path = "/" + path

    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        event_store=None,
        json_response=json_response,
        stateless=stateless,
        security_settings=_transport_security_for_bind_host(bind_host),
    )
    asgi = _StreamableHTTPASGIApp(session_manager)

    @asynccontextmanager
    async def lifespan(_: Starlette):
        async with session_manager.run():
            yield

    return Starlette(
        routes=[Route(path, endpoint=asgi)],
        lifespan=lifespan,
    )
