"""
Shared fixtures for e2e tests.
"""

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def live_client() -> AsyncClient:
    """
    ASGI test client backed by the live Azure PostgreSQL database.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
