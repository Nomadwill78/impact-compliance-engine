from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.core.auth import require_api_key
from app.core.config import settings

@pytest.mark.asyncio
async def test_empty_configuration_fails_closed():
    with patch.object(settings, "API_KEYS", ""), patch.object(settings, "DEBUG", False):
        with pytest.raises(HTTPException) as error:
            await require_api_key(None)
        assert error.value.status_code == 503

@pytest.mark.asyncio
async def test_local_bypass_requires_both_flags():
    with patch.object(settings, "API_KEYS", ""), patch.object(settings, "ALLOW_UNAUTHENTICATED_LOCAL_DEV", True):
        with patch.object(settings, "DEBUG", False):
            with pytest.raises(HTTPException):
                await require_api_key(None)
        with patch.object(settings, "DEBUG", True):
            await require_api_key(None)

@pytest.mark.asyncio
async def test_configured_keys_are_required_even_in_debug():
    with patch.object(settings, "API_KEYS", "test-secret"), patch.object(settings, "DEBUG", True):
        for supplied in [None, "wrong"]:
            with pytest.raises(HTTPException) as error:
                await require_api_key(supplied)
            assert error.value.status_code == 401
        await require_api_key("test-secret")
