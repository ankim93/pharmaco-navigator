"""
Shared fixtures for API-tier router tests.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def async_client() -> AsyncClient:
    """
    Real ASGI transport
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
