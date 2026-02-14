"""Conversation API integration tests."""

import pytest
from httpx import AsyncClient


_worker_counter = 0


async def _create_worker(client: AsyncClient, name_prefix: str = "conv-test-worker") -> str:
    """Helper to create a worker and return its name."""
    global _worker_counter
    _worker_counter += 1
    name = f"{name_prefix}-{_worker_counter}"
    response = await client.post(
        "/api/v1/workers",
        json={"name": name, "type": "claudecode"}
    )
    return response.json()["name"]


class TestConversationAPI:
    """Tests for conversation API endpoints."""

    class TestListConversations:
        """SUT: list_conversations"""

        async def test_empty(self, client: AsyncClient):
            """Should return empty list when no conversations exist."""
            response = await client.get("/api/v1/conversations")
            assert response.status_code == 200
            data = response.json()
            assert data["conversations"] == []
            assert data["total"] == 0

        async def test_after_create(self, client: AsyncClient):
            """Should return conversations after creating one."""
            worker_name = await _create_worker(client)
            await client.post(
                "/api/v1/conversations",
                json={"worker_name": worker_name, "project_path": "/tmp"}
            )

            response = await client.get("/api/v1/conversations")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["conversations"]) == 1

        async def test_filter_by_worker(self, client: AsyncClient):
            """Should filter conversations by worker_name."""
            worker1_name = await _create_worker(client)
            worker2_name = await _create_worker(client)

            await client.post(
                "/api/v1/conversations",
                json={"worker_name": worker1_name, "project_path": "/tmp"}
            )
            await client.post(
                "/api/v1/conversations",
                json={"worker_name": worker2_name, "project_path": "/tmp"}
            )

            response = await client.get("/api/v1/conversations")
            assert response.json()["total"] == 2

            response = await client.get(f"/api/v1/conversations?worker_name={worker1_name}")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["conversations"][0]["worker_name"] == worker1_name

    class TestCreateConversation:
        """SUT: create_conversation"""

        async def test_success(self, client: AsyncClient):
            """Should create a conversation and return 201."""
            worker_name = await _create_worker(client)

            response = await client.post(
                "/api/v1/conversations",
                json={
                    "worker_name": worker_name,
                    "project_path": "/tmp",
                    "name": "Test Conversation"
                }
            )
            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert data["name"] == "Test Conversation"
            assert data["worker_name"] == worker_name
            assert data["project_path"] == "/tmp"

        async def test_no_name_defaults_to_null(self, client: AsyncClient):
            """Creating without name should default to null."""
            worker_name = await _create_worker(client)

            response = await client.post(
                "/api/v1/conversations",
                json={"worker_name": worker_name, "project_path": "/tmp"}
            )
            assert response.status_code == 201
            assert response.json()["name"] is None

        async def test_invalid_worker(self, client: AsyncClient):
            """Non-existent worker should return 404."""
            response = await client.post(
                "/api/v1/conversations",
                json={"worker_name": "non-existent-worker", "project_path": "/tmp"}
            )
            assert response.status_code == 404

        async def test_invalid_path(self, client: AsyncClient):
            """Non-existent path should return 400."""
            worker_name = await _create_worker(client)

            response = await client.post(
                "/api/v1/conversations",
                json={
                    "worker_name": worker_name,
                    "project_path": "/non/existent/path"
                }
            )
            assert response.status_code == 400
            assert "project_path does not exist" in response.json()["detail"]

        async def test_path_is_file(self, client: AsyncClient):
            """File path (not directory) should return 400."""
            worker_name = await _create_worker(client)

            response = await client.post(
                "/api/v1/conversations",
                json={
                    "worker_name": worker_name,
                    "project_path": "/etc/hostname"
                }
            )
            assert response.status_code == 400
            assert "not a directory" in response.json()["detail"]

        async def test_unique_ids(self, client: AsyncClient):
            """Two consecutive creates should produce unique IDs."""
            worker_name = await _create_worker(client)

            response1 = await client.post(
                "/api/v1/conversations",
                json={
                    "worker_name": worker_name,
                    "project_path": "/tmp",
                    "name": "First Conversation"
                }
            )
            assert response1.status_code == 201
            id1 = response1.json()["id"]

            response2 = await client.post(
                "/api/v1/conversations",
                json={
                    "worker_name": worker_name,
                    "project_path": "/tmp",
                    "name": "Second Conversation"
                }
            )
            assert response2.status_code == 201
            id2 = response2.json()["id"]

            assert id1 != id2

            get1 = await client.get(f"/api/v1/conversations/{id1}")
            get2 = await client.get(f"/api/v1/conversations/{id2}")
            assert get1.status_code == 200
            assert get2.status_code == 200
            assert get1.json()["name"] == "First Conversation"
            assert get2.json()["name"] == "Second Conversation"

            list_response = await client.get("/api/v1/conversations")
            assert list_response.json()["total"] == 2

    class TestGetConversation:
        """SUT: get_conversation"""

        async def test_found(self, client: AsyncClient):
            """Should return conversation by ID."""
            worker_name = await _create_worker(client)
            create_response = await client.post(
                "/api/v1/conversations",
                json={
                    "worker_name": worker_name,
                    "project_path": "/tmp",
                    "name": "Test Conversation"
                }
            )
            conversation_id = create_response.json()["id"]

            response = await client.get(f"/api/v1/conversations/{conversation_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == conversation_id
            assert data["worker_name"] == worker_name
            assert data["name"] == "Test Conversation"

        async def test_not_found(self, client: AsyncClient):
            """Non-existent ID should return 404."""
            response = await client.get("/api/v1/conversations/non-existent-id")
            assert response.status_code == 404

    class TestDeleteConversation:
        """SUT: delete_conversation"""

        async def test_success(self, client: AsyncClient):
            """Should delete and return status deleted."""
            worker_name = await _create_worker(client)
            create_response = await client.post(
                "/api/v1/conversations",
                json={"worker_name": worker_name, "project_path": "/tmp"}
            )
            conversation_id = create_response.json()["id"]

            response = await client.delete(f"/api/v1/conversations/{conversation_id}")
            assert response.status_code == 200
            assert response.json()["status"] == "deleted"

            get_response = await client.get(f"/api/v1/conversations/{conversation_id}")
            assert get_response.status_code == 404

        async def test_not_found(self, client: AsyncClient):
            """Non-existent ID should return 404."""
            response = await client.delete("/api/v1/conversations/non-existent-id")
            assert response.status_code == 404

    class TestRenameConversation:
        """SUT: rename_conversation"""

        async def test_success(self, client: AsyncClient):
            """Should rename and persist new name."""
            worker_name = await _create_worker(client)
            create_response = await client.post(
                "/api/v1/conversations",
                json={
                    "worker_name": worker_name,
                    "project_path": "/tmp",
                    "name": "Original Name"
                }
            )
            conversation_id = create_response.json()["id"]

            response = await client.patch(
                f"/api/v1/conversations/{conversation_id}",
                json={"new_name": "New Name"}
            )
            assert response.status_code == 200

            get_response = await client.get(f"/api/v1/conversations/{conversation_id}")
            assert get_response.json()["name"] == "New Name"

        async def test_not_found(self, client: AsyncClient):
            """Non-existent ID should return 404."""
            response = await client.patch(
                "/api/v1/conversations/non-existent-id",
                json={"new_name": "New Name"}
            )
            assert response.status_code == 404
