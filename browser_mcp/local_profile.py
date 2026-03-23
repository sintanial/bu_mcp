"""Persistent Chromium user-data directory for local (non-cloud) browser sessions."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_local_user_data_dir() -> Path:
    """Directory on disk where local browser profile (cookies, storage) is stored.

    Override with env ``BROWSER_MCP_LOCAL_USER_DATA_DIR``; default ``~/.browser-mcp/local-profile``.
    """
    override = (os.environ.get("BROWSER_MCP_LOCAL_USER_DATA_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".browser-mcp" / "local-profile").resolve()
