"""
API Key Authentication
=======================
Simple header-based API key auth for the /api/v1 routes.

Required by default. An explicit local-development bypass requires DEBUG
and ALLOW_UNAUTHENTICATED_LOCAL_DEV together.
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
    Missing configuration returns 503 unless the explicit local bypass is enabled.
    """
    valid_keys = settings.api_keys_list

    if not valid_keys:
        if settings.DEBUG and settings.ALLOW_UNAUTHENTICATED_LOCAL_DEV:
            logger.warning("Explicit unauthenticated local development mode is enabled.")
            return
        raise HTTPException(status_code=503, detail="API authentication is not configured.")

    if not x_api_key or x_api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Missing or invalid API key."},
        )
