"""Browser Use Cloud v2: create/stop remote browsers (X-Browser-Use-API-Key)."""

from __future__ import annotations

import logging

import httpx

from browser_mcp.constants import BROWSER_USE_CLOUD_API_BASE
from browser_use.browser.cloud.views import (
    CloudBrowserAuthError,
    CloudBrowserError,
    CloudBrowserResponse,
    CreateBrowserRequest,
)

logger = logging.getLogger(__name__)


async def create_browser(api_key: str, request: CreateBrowserRequest) -> CloudBrowserResponse:
    """POST /api/v2/browsers with X-Browser-Use-API-Key."""
    url = f"{BROWSER_USE_CLOUD_API_BASE}/api/v2/browsers"
    headers = {
        "X-Browser-Use-API-Key": api_key,
        "Content-Type": "application/json",
    }
    body = request.model_dump(exclude_unset=True)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=body)
    if response.status_code == 401:
        raise CloudBrowserAuthError(
            "Authentication failed. Check browser_use_api_key or BROWSER_USE_API_KEY."
        )
    if response.status_code == 403:
        raise CloudBrowserAuthError("Access forbidden. Check your browser-use cloud subscription.")
    if not response.is_success:
        msg = f"Failed to create cloud browser: HTTP {response.status_code}"
        try:
            err = response.json()
            if "detail" in err:
                msg += f" - {err['detail']}"
        except Exception:
            pass
        raise CloudBrowserError(msg)
    data = response.json()
    return CloudBrowserResponse(**data)


async def stop_browser(api_key: str, browser_session_id: str) -> None:
    """PATCH /api/v2/browsers/{id} action=stop."""
    url = f"{BROWSER_USE_CLOUD_API_BASE}/api/v2/browsers/{browser_session_id}"
    headers = {
        "X-Browser-Use-API-Key": api_key,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(url, headers=headers, json={"action": "stop"})
    if response.status_code in (401, 403):
        logger.warning("Cloud browser stop auth failed for session %s", browser_session_id[:8])
        return
    if response.status_code == 404:
        return
    if not response.is_success:
        logger.warning("Cloud browser stop failed: HTTP %s", response.status_code)
