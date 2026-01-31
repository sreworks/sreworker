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
            json={"name": name, "type": "claude"}
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
                "project_path": "/tmp/test-project",
                "name": "Test Conversation"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Conversation"
        assert data["worker_name"] == worker_name
        assert data["project_path"] == "/tmp/test-project"

    async def test_create_conversation_auto_name(self, client: AsyncClient):
        """Test creating conversation with auto-generated name."""
        worker_name = await self._create_worker(client)

        response = await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": worker_name,
                "project_path": "/tmp/test-project"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "Conversation" in data["name"]

    async def test_create_conversation_invalid_worker(self, client: AsyncClient):
        """Test creating conversation with invalid worker fails."""
        response = await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": "non-existent-worker",
                "project_path": "/tmp/test-project"
            }
        )
        assert response.status_code == 404

    async def test_get_conversation(self, client: AsyncClient):
        """Test getting a conversation by ID."""
        worker_name = await self._create_worker(client)

        # Create conversation
        create_response = await client.post(
            "/api/v1/conversations",
            json={
                "worker_name": worker_name,
                "project_path": "/tmp/test-project",
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
                "project_path": "/tmp/test-project"
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
            json={"worker_name": worker1_id, "project_path": "/tmp/project1"}
        )
        await client.post(
            "/api/v1/conversations",
            json={"worker_name": worker2_id, "project_path": "/tmp/project2"}
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
            json={"worker_name": worker_name, "project_path": "/tmp/test-project"}
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
                "project_path": "/tmp/test-project",
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

    async def test_get_conversation_messages_empty(self, client: AsyncClient):
        """Test getting messages from empty conversation."""
        worker_name = await self._create_worker(client)

        # Create conversation
        create_response = await client.post(
            "/api/v1/conversations",
            json={"worker_name": worker_name, "project_path": "/tmp/test-project"}
        )
        conversation_id = create_response.json()["id"]

        # Get messages
        response = await client.get(f"/api/v1/conversations/{conversation_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id
        assert data["messages"] == []
        assert data["total"] == 0

    async def test_get_conversation_messages_not_found(self, client: AsyncClient):
        """Test getting messages from non-existent conversation returns 404."""
        response = await client.get("/api/v1/conversations/non-existent-id/messages")
        assert response.status_code == 404

    async def test_create_message(self, client: AsyncClient):
        """Test creating a message in a conversation."""
        worker_name = await self._create_worker(client)

        # Create conversation
        create_response = await client.post(
            "/api/v1/conversations",
            json={"worker_name": worker_name, "project_path": "/tmp/test-project"}
        )
        conversation_id = create_response.json()["id"]

        # Create message
        response = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"role": "user", "content": "Hello, world!"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello, world!"
        assert data["conversation_id"] == conversation_id
        assert data["worker_name"] == worker_name

    async def test_create_message_not_found(self, client: AsyncClient):
        """Test creating message in non-existent conversation returns 404."""
        response = await client.post(
            "/api/v1/conversations/non-existent-id/messages",
            json={"role": "user", "content": "Hello"}
        )
        assert response.status_code == 404

    async def test_create_and_get_messages(self, client: AsyncClient):
        """Test creating multiple messages and retrieving them."""
        worker_name = await self._create_worker(client)

        # Create conversation
        create_response = await client.post(
            "/api/v1/conversations",
            json={"worker_name": worker_name, "project_path": "/tmp/test-project"}
        )
        conversation_id = create_response.json()["id"]

        # Create messages
        await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"role": "user", "content": "Hello"}
        )
        await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"role": "assistant", "content": "Hi there!"}
        )

        # Get messages (reverse order: newest first)
        response = await client.get(f"/api/v1/conversations/{conversation_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "assistant"
        assert data["messages"][0]["content"] == "Hi there!"
        assert data["messages"][1]["role"] == "user"
        assert data["messages"][1]["content"] == "Hello"

    async def test_create_message_with_metadata(self, client: AsyncClient):
        """Test creating a message with metadata."""
        worker_name = await self._create_worker(client)

        # Create conversation
        create_response = await client.post(
            "/api/v1/conversations",
            json={"worker_name": worker_name, "project_path": "/tmp/test-project"}
        )
        conversation_id = create_response.json()["id"]

        # Create message with metadata
        response = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={
                "role": "user",
                "content": "Test message",
                "metadata": {"source": "test", "priority": 1}
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"]["source"] == "test"
        assert data["metadata"]["priority"] == 1
