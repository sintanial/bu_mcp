"""MCP stdio server: register tools, resources, and run."""

from __future__ import annotations

from collections.abc import Iterable

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from pydantic import AnyUrl

from browser_mcp import __version__
from browser_mcp.instructions import AUTH_RESOURCE_URI, MCP_SERVER_INSTRUCTIONS
from browser_mcp.sessions import SessionRegistry
from browser_mcp.tool_definitions import list_tools
from browser_mcp.tool_handlers import handle_tool_call

_registry = SessionRegistry()


def build_mcp_server() -> Server:
    server = Server("browser-mcp")

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


async def run_stdio() -> None:
    server = build_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="browser-mcp",
                server_version=__version__,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
                instructions=MCP_SERVER_INSTRUCTIONS,
            ),
        )
