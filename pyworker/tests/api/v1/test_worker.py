"""Worker API integration tests."""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Health check endpoint tests."""

    async def test_health_check(self, client: AsyncClient):
        """Test health check returns healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"


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
                "name": "test-worker",
                "type": "claudecode",
                "env_vars": {"TEST_VAR": "test_value"},
                "command_params": ["--verbose"]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test-worker"
        assert data["type"] == "claudecode"
        assert data["env_vars"] == {"TEST_VAR": "test_value"}
        assert data["command_params"] == ["--verbose"]

    async def test_create_worker_default_type(self, client: AsyncClient):
        """Test creating worker with default type."""
        response = await client.post(
            "/api/v1/workers",
            json={"name": "default-type-worker"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "claudecode"

    async def test_create_worker_invalid_name_with_space(self, client: AsyncClient):
        """Test creating worker with invalid name (contains space) fails."""
        response = await client.post(
            "/api/v1/workers",
            json={"name": "invalid worker", "type": "claudecode"}
        )
        assert response.status_code == 422

    async def test_create_worker_invalid_name_starts_with_number(self, client: AsyncClient):
        """Test creating worker with invalid name (starts with number) fails."""
        response = await client.post(
            "/api/v1/workers",
            json={"name": "123worker", "type": "claudecode"}
        )
        assert response.status_code == 422

    async def test_create_worker_invalid_name_special_chars(self, client: AsyncClient):
        """Test creating worker with invalid name (special chars) fails."""
        response = await client.post(
            "/api/v1/workers",
            json={"name": "worker@test", "type": "claudecode"}
        )
        assert response.status_code == 422

    async def test_create_worker_valid_name_with_hyphen(self, client: AsyncClient):
        """Test creating worker with valid name containing hyphen."""
        response = await client.post(
            "/api/v1/workers",
            json={"name": "my-worker-1", "type": "claudecode"}
        )
        assert response.status_code == 201
        assert response.json()["name"] == "my-worker-1"

    async def test_create_worker_valid_name_with_underscore(self, client: AsyncClient):
        """Test creating worker with valid name containing underscore."""
        response = await client.post(
            "/api/v1/workers",
            json={"name": "my_worker_2", "type": "claudecode"}
        )
        assert response.status_code == 201
        assert response.json()["name"] == "my_worker_2"

    async def test_create_worker_duplicate_name(self, client: AsyncClient):
        """Test creating worker with duplicate name fails."""
        # Create first worker
        response1 = await client.post(
            "/api/v1/workers",
            json={"name": "duplicate-test", "type": "claudecode"}
        )
        assert response1.status_code == 201

        # Try to create second worker with same name
        response2 = await client.post(
            "/api/v1/workers",
            json={"name": "duplicate-test", "type": "claudecode"}
        )
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]

    async def test_get_worker(self, client: AsyncClient):
        """Test getting a worker by ID."""
        # Create worker first
        create_response = await client.post(
            "/api/v1/workers",
            json={"name": "get-test", "type": "claudecode"}
        )
        worker_name = create_response.json()["name"]

        # Get worker
        response = await client.get(f"/api/v1/workers/{worker_name}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == worker_name
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
            json={"name": "delete-test", "type": "claudecode"}
        )
        worker_name = create_response.json()["name"]

        # Delete worker
        response = await client.delete(f"/api/v1/workers/{worker_name}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

        # Verify worker is deleted
        get_response = await client.get(f"/api/v1/workers/{worker_name}")
        assert get_response.status_code == 404

    async def test_delete_worker_not_found(self, client: AsyncClient):
        """Test deleting non-existent worker returns 404."""
        response = await client.delete("/api/v1/workers/non-existent-id")
        assert response.status_code == 404

    async def test_list_workers_after_create(self, client: AsyncClient):
        """Test listing workers after creating one."""
        # Create worker
        await client.post(
            "/api/v1/workers",
            json={"name": "list-test", "type": "claudecode"}
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
                "name": "persist-test",
                "type": "claudecode",
                "env_vars": {"API_KEY": "secret123", "DEBUG": "true"},
                "command_params": ["--model", "claude-3"]
            }
        )
        worker_name = create_response.json()["name"]

        # Retrieve and verify
        response = await client.get(f"/api/v1/workers/{worker_name}")
        assert response.status_code == 200
        data = response.json()
        assert data["env_vars"]["API_KEY"] == "secret123"
        assert data["env_vars"]["DEBUG"] == "true"
        assert "--model" in data["command_params"]
        assert "claude-3" in data["command_params"]
