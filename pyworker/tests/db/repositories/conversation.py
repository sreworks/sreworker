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


def _make_conv(**overrides):
    """Factory for ConversationDO with sensible defaults."""
    defaults = dict(id="c1", worker_id="w1", project_path="/tmp")
    defaults.update(overrides)
    return ConversationDO(**defaults)


class TestConversationRepository:
    """Tests for ConversationRepository."""

    class TestCreate:
        """SUT: ConversationRepository.create"""

        def test_returns_true(self, repo):
            """create() should return True on success."""
            assert repo.create(_make_conv(name="Test Conv")) is True

        def test_fields_persisted(self, repo):
            """Created conversation should be retrievable with all fields."""
            repo.create(_make_conv(name="Test Conv"))
            result = repo.get("c1")
            assert result is not None
            assert result.id == "c1"
            assert result.worker_id == "w1"
            assert result.project_path == "/tmp"
            assert result.name == "Test Conv"

    class TestGet:
        """SUT: ConversationRepository.get"""

        def test_found(self, repo):
            """get() should return the conversation when it exists."""
            repo.create(_make_conv())
            result = repo.get("c1")
            assert result is not None
            assert result.id == "c1"

        def test_not_found(self, repo):
            """get() should return None for non-existent id."""
            assert repo.get("nonexistent") is None

    class TestListAll:
        """SUT: ConversationRepository.list_all"""

        def test_ordered_by_last_activity_desc(self, repo):
            """Results should be ordered by last_activity DESC."""
            now = datetime.utcnow()
            repo.create(_make_conv(
                id="c1", last_activity=now - timedelta(hours=1)
            ))
            repo.create(_make_conv(id="c2", last_activity=now))

            results = repo.list_all()
            assert len(results) == 2
            assert results[0].id == "c2"
            assert results[1].id == "c1"

    class TestListByWorker:
        """SUT: ConversationRepository.list_by_worker"""

        def test_filters_by_worker(self, repo):
            """Should only return conversations for the given worker."""
            repo.create(_make_conv(id="c1", worker_id="w1"))
            repo.create(_make_conv(id="c2", worker_id="w2"))

            results = repo.list_by_worker("w1")
            assert len(results) == 1
            assert results[0].worker_id == "w1"

    class TestGetCurrent:
        """SUT: ConversationRepository.get_current"""

        def test_returns_current_id(self, repo):
            """Should return the id of the current conversation."""
            repo.create(_make_conv(id="c1"))
            repo.create(_make_conv(id="c2"))
            repo.switch_current("w1", "c1")
            assert repo.get_current("w1") == "c1"

    class TestSwitchCurrent:
        """SUT: ConversationRepository.switch_current"""

        def test_sets_new_current(self, repo):
            """switch_current() should return True and set new current."""
            repo.create(_make_conv(id="c1"))
            repo.create(_make_conv(id="c2"))
            assert repo.switch_current("w1", "c1") is True
            assert repo.get_current("w1") == "c1"

        def test_unsets_old_current(self, repo):
            """Switching should unset the previous current conversation."""
            repo.create(_make_conv(id="c1"))
            repo.create(_make_conv(id="c2"))
            repo.switch_current("w1", "c1")
            repo.switch_current("w1", "c2")

            assert repo.get_current("w1") == "c2"
            old = repo.get("c1")
            assert old.is_current is False

    class TestDelete:
        """SUT: ConversationRepository.delete"""

        def test_returns_true(self, repo):
            """delete() should return True on success."""
            repo.create(_make_conv())
            assert repo.delete("c1") is True

        def test_removes_conversation(self, repo):
            """Deleted conversation should not be retrievable."""
            repo.create(_make_conv())
            repo.delete("c1")
            assert repo.get("c1") is None

    class TestUpdate:
        """SUT: ConversationRepository.update"""

        def test_name(self, repo):
            """Updating name should take effect."""
            repo.create(_make_conv())
            assert repo.update("c1", {"name": "New Name"}) is True
            assert repo.get("c1").name == "New Name"

        def test_last_activity(self, repo):
            """Updating last_activity should take effect."""
            repo.create(_make_conv())
            new_time = datetime(2025, 1, 1, 12, 0, 0)
            assert repo.update("c1", {"last_activity": new_time}) is True
            assert repo.get("c1").last_activity.year == 2025

        def test_raw_conversation_id(self, repo):
            """Updating raw_conversation_id should take effect."""
            repo.create(_make_conv())
            assert repo.update("c1", {"raw_conversation_id": "raw-123"}) is True
            assert repo.get("c1").raw_conversation_id == "raw-123"

        def test_metadata(self, repo):
            """Updating metadata should JSON-serialize correctly."""
            repo.create(_make_conv())
            meta = {"key": "value", "nested": {"a": 1}}
            assert repo.update("c1", {"metadata": meta}) is True
            assert repo.get("c1").metadata == meta

        def test_empty_no_op(self, repo):
            """Updating with empty dict should return True (no-op)."""
            repo.create(_make_conv())
            assert repo.update("c1", {}) is True
