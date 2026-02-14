"""Tests for FastAPI application entry point."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    """Provide an async test client for the app (no lifespan)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestMain:
    """SUT: app (main.py)"""

    async def test_health_check(self, client: AsyncClient):
        """GET /health should return 200 with healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
