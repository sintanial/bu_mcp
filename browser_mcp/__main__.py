"""Entry: python -m browser_mcp"""

from __future__ import annotations

import asyncio
import os


def main() -> None:
    os.environ.setdefault("BROWSER_USE_SETUP_LOGGING", "false")
    from browser_mcp.server import run_stdio

    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
