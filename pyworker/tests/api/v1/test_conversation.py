"""Conversation API integration tests."""

import pytest
from httpx import AsyncClient


class TestConversationCRUD:
    """Conversation CRUD operation tests."""

    _worker_counter = 0

    async def _create_worker(self, client: AsyncClient, name_prefix: str = "conv-test-worker") -> str:
        """Helper to create a worker and return its ID."""
        TestConversationCRUD._worker_counter += 1
        name = f"{name_prefix}-{TestConversationCRUD._worker_counter}"
        response = await client.post(
            "/api/v1/workers",
            json={"name": name, "type": "claudecode"}
        )
        return response.json()["name"]

    async def test_list_conversations_empty(self, client: AsyncClient):
        """Test listing conversations when empty."""
        response = await client.get("/api/v1/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["conversations"] == []
        assert data["total"] == 0

    async def test_create_conversation(self, client: AsyncClient):
        """Test creating a conversation."""
        worker_name = await self._create_worker(client)

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

    async def test_create_conversation_no_name(self, client: AsyncClient):
        """Test creating conversation without name defaults to null."""
        worker_name = await self._create_worker(client)

        response = await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": worker_name,
                "project_path": "/tmp"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] is None

    async def test_create_conversation_invalid_worker(self, client: AsyncClient):
        """Test creating conversation with invalid worker fails."""
        response = await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": "non-existent-worker",
                "project_path": "/tmp"
            }
        )
        assert response.status_code == 404

    async def test_create_conversation_invalid_path(self, client: AsyncClient):
        """Test creating conversation with non-existent path fails."""
        worker_name = await self._create_worker(client)

        response = await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": worker_name,
                "project_path": "/non/existent/path"
            }
        )
        assert response.status_code == 400
        assert "project_path does not exist" in response.json()["detail"]

    async def test_get_conversation(self, client: AsyncClient):
        """Test getting a conversation by ID."""
        worker_name = await self._create_worker(client)

        # Create conversation
        create_response = await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": worker_name,
                "project_path": "/tmp",
                "name": "Test Conversation"
            }
        )
        conversation_id = create_response.json()["id"]

        # Get conversation
        response = await client.get(f"/api/v1/conversations/{conversation_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conversation_id
        assert data["worker_name"] == worker_name
        assert data["name"] == "Test Conversation"

    async def test_get_conversation_not_found(self, client: AsyncClient):
        """Test getting non-existent conversation returns 404."""
        response = await client.get("/api/v1/conversations/non-existent-id")
        assert response.status_code == 404

    async def test_list_conversations_after_create(self, client: AsyncClient):
        """Test listing conversations after creating one."""
        worker_name = await self._create_worker(client)

        # Create conversation
        await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": worker_name,
                "project_path": "/tmp"
            }
        )

        # List conversations
        response = await client.get("/api/v1/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["conversations"]) == 1

    async def test_list_conversations_filter_by_worker(self, client: AsyncClient):
        """Test filtering conversations by worker_name."""
        worker1_id = await self._create_worker(client)
        worker2_id = await self._create_worker(client)

        # Create conversations for both workers
        await client.post(
            "/api/v1/conversations",
            json={"worker_name": worker1_id, "project_path": "/tmp"}
        )
        await client.post(
            "/api/v1/conversations",
            json={"worker_name": worker2_id, "project_path": "/tmp"}
        )

        # List all
        response = await client.get("/api/v1/conversations")
        assert response.json()["total"] == 2

        # Filter by worker1
        response = await client.get(f"/api/v1/conversations?worker_name={worker1_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["conversations"][0]["worker_name"] == worker1_id

    async def test_delete_conversation(self, client: AsyncClient):
        """Test deleting a conversation."""
        worker_name = await self._create_worker(client)

        # Create conversation
        create_response = await client.post(
            "/api/v1/conversations",
            json={"worker_name": worker_name, "project_path": "/tmp"}
        )
        conversation_id = create_response.json()["id"]

        # Delete conversation
        response = await client.delete(f"/api/v1/conversations/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify deleted
        get_response = await client.get(f"/api/v1/conversations/{conversation_id}")
        assert get_response.status_code == 404

    async def test_delete_conversation_not_found(self, client: AsyncClient):
        """Test deleting non-existent conversation returns 404."""
        response = await client.delete("/api/v1/conversations/non-existent-id")
        assert response.status_code == 404

    async def test_rename_conversation(self, client: AsyncClient):
        """Test renaming a conversation."""
        worker_name = await self._create_worker(client)

        # Create conversation
        create_response = await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": worker_name,
                "project_path": "/tmp",
                "name": "Original Name"
            }
        )
        conversation_id = create_response.json()["id"]

        # Rename
        response = await client.patch(
            f"/api/v1/conversations/{conversation_id}",
            json={"new_name": "New Name"}
        )
        assert response.status_code == 200

        # Verify renamed
        get_response = await client.get(f"/api/v1/conversations/{conversation_id}")
        assert get_response.json()["name"] == "New Name"

    async def test_rename_conversation_not_found(self, client: AsyncClient):
        """Test renaming non-existent conversation returns 404."""
        response = await client.patch(
            "/api/v1/conversations/non-existent-id",
            json={"new_name": "New Name"}
        )
        assert response.status_code == 404

    async def test_create_two_conversations_consecutively(self, client: AsyncClient):
        """Test creating two conversations consecutively with unique IDs."""
        worker_name = await self._create_worker(client)

        # Create first conversation
        response1 = await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": worker_name,
                "project_path": "/tmp",
                "name": "First Conversation"
            }
        )
        assert response1.status_code == 201
        data1 = response1.json()
        conversation_id_1 = data1["id"]

        # Create second conversation
        response2 = await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": worker_name,
                "project_path": "/tmp",
                "name": "Second Conversation"
            }
        )
        assert response2.status_code == 201
        data2 = response2.json()
        conversation_id_2 = data2["id"]

        # Verify IDs are different
        assert conversation_id_1 != conversation_id_2

        # Verify both exist
        get1 = await client.get(f"/api/v1/conversations/{conversation_id_1}")
        get2 = await client.get(f"/api/v1/conversations/{conversation_id_2}")
        assert get1.status_code == 200
        assert get2.status_code == 200
        assert get1.json()["name"] == "First Conversation"
        assert get2.json()["name"] == "Second Conversation"

        # Verify total count
        list_response = await client.get("/api/v1/conversations")
        assert list_response.json()["total"] == 2
