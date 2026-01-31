"""Worker API integration tests."""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Health check endpoint tests."""

    async def test_health_check(self, client: AsyncClient):
        """Test health check returns healthy status."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "v1"


class TestWorkerTypes:
    """Worker types endpoint tests."""

    async def test_list_worker_types(self, client: AsyncClient):
        """Test listing available worker types."""
        response = await client.get("/api/v1/workers/types")
        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert "claudecode" in data["types"]
        assert "default" in data


class TestWorkerCRUD:
    """Worker CRUD operation tests."""

    async def test_list_workers_empty(self, client: AsyncClient):
        """Test listing workers when empty."""
        response = await client.get("/api/v1/workers")
        assert response.status_code == 200
        data = response.json()
        assert data["workers"] == []

    async def test_create_worker(self, client: AsyncClient):
        """Test creating a worker."""
        response = await client.post(
            "/api/v1/workers",
            json={
                "type": "claudecode",
                "env_vars": {"TEST_VAR": "test_value"},
                "command_params": ["--verbose"]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "claudecode"
        assert data["env_vars"] == {"TEST_VAR": "test_value"}
        assert data["command_params"] == ["--verbose"]
        assert "id" in data

    async def test_create_worker_invalid_type(self, client: AsyncClient):
        """Test creating worker with invalid type fails."""
        response = await client.post(
            "/api/v1/workers",
            json={"type": "invalid_type"}
        )
        assert response.status_code == 422

    async def test_get_worker(self, client: AsyncClient):
        """Test getting a worker by ID."""
        # Create worker first
        create_response = await client.post(
            "/api/v1/workers",
            json={"type": "claudecode"}
        )
        worker_id = create_response.json()["id"]

        # Get worker
        response = await client.get(f"/api/v1/workers/{worker_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == worker_id
        assert data["type"] == "claudecode"

    async def test_get_worker_not_found(self, client: AsyncClient):
        """Test getting non-existent worker returns 404."""
        response = await client.get("/api/v1/workers/non-existent-id")
        assert response.status_code == 404

    async def test_delete_worker(self, client: AsyncClient):
        """Test deleting a worker."""
        # Create worker first
        create_response = await client.post(
            "/api/v1/workers",
            json={"type": "claudecode"}
        )
        worker_id = create_response.json()["id"]

        # Delete worker
        response = await client.delete(f"/api/v1/workers/{worker_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

        # Verify worker is deleted
        get_response = await client.get(f"/api/v1/workers/{worker_id}")
        assert get_response.status_code == 404

    async def test_list_workers_after_create(self, client: AsyncClient):
        """Test listing workers after creating one."""
        # Create worker
        await client.post(
            "/api/v1/workers",
            json={"type": "claudecode"}
        )

        # List workers
        response = await client.get("/api/v1/workers")
        assert response.status_code == 200
        data = response.json()
        assert len(data["workers"]) == 1

    async def test_worker_persistence(self, client: AsyncClient):
        """Test worker data is persisted correctly."""
        # Create worker with specific data
        create_response = await client.post(
            "/api/v1/workers",
            json={
                "type": "claudecode",
                "env_vars": {"API_KEY": "secret123", "DEBUG": "true"},
                "command_params": ["--model", "claude-3"]
            }
        )
        worker_id = create_response.json()["id"]

        # Retrieve and verify
        response = await client.get(f"/api/v1/workers/{worker_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["env_vars"]["API_KEY"] == "secret123"
        assert data["env_vars"]["DEBUG"] == "true"
        assert "--model" in data["command_params"]
        assert "claude-3" in data["command_params"]
