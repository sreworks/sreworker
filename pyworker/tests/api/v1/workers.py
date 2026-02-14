"""Worker API integration tests."""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """SUT: health_check (main.py)"""

    async def test_health_check(self, client: AsyncClient):
        """Should return 200 with healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"


class TestWorkerAPI:
    """Tests for worker API endpoints."""

    class TestListWorkers:
        """SUT: list_workers"""

        async def test_empty(self, client: AsyncClient):
            """Should return empty list when no workers exist."""
            response = await client.get("/api/v1/workers")
            assert response.status_code == 200
            data = response.json()
            assert data["workers"] == []

        async def test_after_create(self, client: AsyncClient):
            """Should return workers after creating one."""
            await client.post(
                "/api/v1/workers",
                json={"name": "list-test", "type": "claudecode"}
            )

            response = await client.get("/api/v1/workers")
            assert response.status_code == 200
            data = response.json()
            assert len(data["workers"]) == 1

    class TestCreateWorker:
        """SUT: create_worker"""

        async def test_success(self, client: AsyncClient):
            """Should create a worker with all fields."""
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

        async def test_default_type(self, client: AsyncClient):
            """Should default to claudecode type."""
            response = await client.post(
                "/api/v1/workers",
                json={"name": "default-type-worker"}
            )
            assert response.status_code == 201
            assert response.json()["type"] == "claudecode"

        async def test_invalid_name_with_space(self, client: AsyncClient):
            """Name with space should return 422."""
            response = await client.post(
                "/api/v1/workers",
                json={"name": "invalid worker", "type": "claudecode"}
            )
            assert response.status_code == 422

        async def test_invalid_name_starts_with_number(self, client: AsyncClient):
            """Name starting with number should return 422."""
            response = await client.post(
                "/api/v1/workers",
                json={"name": "123worker", "type": "claudecode"}
            )
            assert response.status_code == 422

        async def test_invalid_name_special_chars(self, client: AsyncClient):
            """Name with special chars should return 422."""
            response = await client.post(
                "/api/v1/workers",
                json={"name": "worker@test", "type": "claudecode"}
            )
            assert response.status_code == 422

        async def test_valid_name_with_hyphen(self, client: AsyncClient):
            """Name with hyphen should be accepted."""
            response = await client.post(
                "/api/v1/workers",
                json={"name": "my-worker-1", "type": "claudecode"}
            )
            assert response.status_code == 201
            assert response.json()["name"] == "my-worker-1"

        async def test_valid_name_with_underscore(self, client: AsyncClient):
            """Name with underscore should be accepted."""
            response = await client.post(
                "/api/v1/workers",
                json={"name": "my_worker_2", "type": "claudecode"}
            )
            assert response.status_code == 201
            assert response.json()["name"] == "my_worker_2"

        async def test_duplicate_name(self, client: AsyncClient):
            """Duplicate name should return 400."""
            response1 = await client.post(
                "/api/v1/workers",
                json={"name": "duplicate-test", "type": "claudecode"}
            )
            assert response1.status_code == 201

            response2 = await client.post(
                "/api/v1/workers",
                json={"name": "duplicate-test", "type": "claudecode"}
            )
            assert response2.status_code == 400
            assert "already exists" in response2.json()["detail"]

        async def test_persistence(self, client: AsyncClient):
            """Created worker data should be persisted correctly."""
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

            response = await client.get(f"/api/v1/workers/{worker_name}")
            assert response.status_code == 200
            data = response.json()
            assert data["env_vars"]["API_KEY"] == "secret123"
            assert data["env_vars"]["DEBUG"] == "true"
            assert "--model" in data["command_params"]
            assert "claude-3" in data["command_params"]

    class TestGetWorker:
        """SUT: get_worker"""

        async def test_found(self, client: AsyncClient):
            """Should return worker by name."""
            create_response = await client.post(
                "/api/v1/workers",
                json={"name": "get-test", "type": "claudecode"}
            )
            worker_name = create_response.json()["name"]

            response = await client.get(f"/api/v1/workers/{worker_name}")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == worker_name
            assert data["type"] == "claudecode"

        async def test_not_found(self, client: AsyncClient):
            """Non-existent name should return 404."""
            response = await client.get("/api/v1/workers/non-existent-id")
            assert response.status_code == 404

    class TestDeleteWorker:
        """SUT: delete_worker"""

        async def test_success(self, client: AsyncClient):
            """Should delete and return status deleted."""
            create_response = await client.post(
                "/api/v1/workers",
                json={"name": "delete-test", "type": "claudecode"}
            )
            worker_name = create_response.json()["name"]

            response = await client.delete(f"/api/v1/workers/{worker_name}")
            assert response.status_code == 200
            assert response.json()["status"] == "deleted"

            get_response = await client.get(f"/api/v1/workers/{worker_name}")
            assert get_response.status_code == 404

        async def test_not_found(self, client: AsyncClient):
            """Non-existent name should return 404."""
            response = await client.delete("/api/v1/workers/non-existent-id")
            assert response.status_code == 404
