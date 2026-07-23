"""
API Key Authentication
=======================
Simple header-based API key auth for the /api/v1 routes.

Enabled automatically when settings.API_KEYS is non-empty. When no keys are
configured (e.g. local development), requests are allowed through but a
warning is emitted so this is never silently insecure in production.
"""
from __future__ import annotations

import logging

from fastapi import Header, HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

_API_KEY_HEADER = "X-API-Key"


async def require_api_key(x_api_key: str | None = Header(default=None, alias=_API_KEY_HEADER)) -> None:
    """FastAPI dependency that validates the X-API-Key header.

    Raises 401 if API_KEYS is configured and the provided key is missing or invalid.
    If no API_KEYS are configured, the check is skipped (dev mode) with a warning.
    """
    valid_keys = settings.api_keys_list

    if not valid_keys:
        logger.warning(
            "API_KEYS is not configured — /api/v1 routes are UNAUTHENTICATED. "
            "Set API_KEYS in the environment to enable auth."
        )
        return

    if not x_api_key or x_api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Missing or invalid API key."},
        )
