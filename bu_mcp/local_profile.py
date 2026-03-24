"""Local Chromium user-data directory when not using Browser Use Cloud."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_local_user_data_dir() -> Path:
    """Directory for local headless Chromium (cookies, storage).

    Override with env ``BU_MCP_LOCAL_USER_DATA_DIR``; default ``~/.bu_mcp/local-profile``.
    """
    override = (os.environ.get("BU_MCP_LOCAL_USER_DATA_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".bu_mcp" / "local-profile").resolve()
