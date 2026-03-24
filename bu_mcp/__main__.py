"""Entry: python -m bu_mcp"""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    from bu_mcp.server import build_streamable_http_app

    host = os.environ.get("BU_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("BU_MCP_PORT", "8765"))
    log_level = os.environ.get("BU_MCP_LOG_LEVEL", "info").lower()
    app = build_streamable_http_app()
    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    main()
