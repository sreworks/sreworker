"""Tests for ConversationRepository."""

import pytest
from datetime import datetime, timedelta

from app.db.connection import DatabaseConnection
from app.db.repositories.conversation import ConversationRepository
from app.db.database_models.conversation import ConversationDO


@pytest.fixture
def db_conn(tmp_path):
    """Provide a fresh database connection."""
    db = DatabaseConnection(str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture
def repo(db_conn):
    """Provide a ConversationRepository."""
    return ConversationRepository(db_conn.conn)


class TestConversationRepository:
    """CRUD tests for ConversationRepository."""

    def test_create_and_get(self, repo):
        """Create a conversation and retrieve it."""
        conv = ConversationDO(
            id="c1", worker_id="w1", project_path="/tmp", name="Test Conv"
        )
        assert repo.create(conv) is True

        result = repo.get("c1")
        assert result is not None
        assert result.id == "c1"
        assert result.worker_id == "w1"
        assert result.project_path == "/tmp"
        assert result.name == "Test Conv"

    def test_get_not_found(self, repo):
        """Getting non-existent conversation returns None."""
        assert repo.get("nonexistent") is None

    def test_list_all(self, repo):
        """List all should return items ordered by last_activity DESC."""
        now = datetime.utcnow()
        conv1 = ConversationDO(
            id="c1", worker_id="w1", project_path="/tmp",
            last_activity=now - timedelta(hours=1)
        )
        conv2 = ConversationDO(
            id="c2", worker_id="w1", project_path="/tmp",
            last_activity=now
        )
        repo.create(conv1)
        repo.create(conv2)

        results = repo.list_all()
        assert len(results) == 2
        assert results[0].id == "c2"
        assert results[1].id == "c1"

    def test_list_by_worker(self, repo):
        """List by worker should filter correctly."""
        repo.create(ConversationDO(id="c1", worker_id="w1", project_path="/tmp"))
        repo.create(ConversationDO(id="c2", worker_id="w2", project_path="/tmp"))

        results = repo.list_by_worker("w1")
        assert len(results) == 1
        assert results[0].worker_id == "w1"

    def test_delete(self, repo):
        """Deleting should make get return None."""
        repo.create(ConversationDO(id="c1", worker_id="w1", project_path="/tmp"))
        assert repo.delete("c1") is True
        assert repo.get("c1") is None

    def test_update_name(self, repo):
        """Updating name should take effect."""
        repo.create(ConversationDO(id="c1", worker_id="w1", project_path="/tmp"))
        assert repo.update("c1", {"name": "New Name"}) is True
        assert repo.get("c1").name == "New Name"

    def test_update_last_activity(self, repo):
        """Updating last_activity should take effect."""
        repo.create(ConversationDO(id="c1", worker_id="w1", project_path="/tmp"))
        new_time = datetime(2025, 1, 1, 12, 0, 0)
        assert repo.update("c1", {"last_activity": new_time}) is True
        result = repo.get("c1")
        assert result.last_activity.year == 2025

    def test_update_raw_conversation_id(self, repo):
        """Updating raw_conversation_id should take effect."""
        repo.create(ConversationDO(id="c1", worker_id="w1", project_path="/tmp"))
        assert repo.update("c1", {"raw_conversation_id": "raw-123"}) is True
        assert repo.get("c1").raw_conversation_id == "raw-123"

    def test_update_metadata(self, repo):
        """Updating metadata should JSON-serialize correctly."""
        repo.create(ConversationDO(id="c1", worker_id="w1", project_path="/tmp"))
        meta = {"key": "value", "nested": {"a": 1}}
        assert repo.update("c1", {"metadata": meta}) is True
        result = repo.get("c1")
        assert result.metadata == meta

    def test_update_empty_no_op(self, repo):
        """Updating with empty dict should return True (no-op)."""
        repo.create(ConversationDO(id="c1", worker_id="w1", project_path="/tmp"))
        assert repo.update("c1", {}) is True

    def test_get_current(self, repo):
        """get_current should return the id of the current conversation."""
        repo.create(ConversationDO(
            id="c1", worker_id="w1", project_path="/tmp"
        ))
        repo.create(ConversationDO(
            id="c2", worker_id="w1", project_path="/tmp"
        ))
        # Use switch_current to set c1 as current
        repo.switch_current("w1", "c1")
        assert repo.get_current("w1") == "c1"

    def test_switch_current(self, repo):
        """switch_current should unset old and set new."""
        repo.create(ConversationDO(
            id="c1", worker_id="w1", project_path="/tmp"
        ))
        repo.create(ConversationDO(
            id="c2", worker_id="w1", project_path="/tmp"
        ))

        # Set c1 as current first
        assert repo.switch_current("w1", "c1") is True
        assert repo.get_current("w1") == "c1"

        # Switch to c2
        assert repo.switch_current("w1", "c2") is True
        assert repo.get_current("w1") == "c2"

        # Verify old one is no longer current
        old = repo.get("c1")
        assert old.is_current is False
