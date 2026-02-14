"""Tests for WorkerRepository."""

import pytest

from app.db.connection import DatabaseConnection
from app.db.repositories.worker import WorkerRepository
from app.db.database_models.worker import WorkerDO


@pytest.fixture
def db_conn(tmp_path):
    """Provide a fresh database connection."""
    db = DatabaseConnection(str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture
def repo(db_conn):
    """Provide a WorkerRepository."""
    return WorkerRepository(db_conn.conn)


class TestWorkerRepository:
    """CRUD tests for WorkerRepository."""

    def test_create_and_get(self, repo):
        """Create a worker and retrieve it with JSON fields parsed."""
        worker = WorkerDO(
            id="w1", type="claudecode",
            env_vars={"KEY": "val"},
            command_params=["--verbose"]
        )
        assert repo.create(worker) is True

        result = repo.get("w1")
        assert result is not None
        assert result.id == "w1"
        assert result.type == "claudecode"
        assert result.env_vars == {"KEY": "val"}
        assert result.command_params == ["--verbose"]

    def test_get_not_found(self, repo):
        """Getting non-existent worker returns None."""
        assert repo.get("nonexistent") is None

    def test_list_all(self, repo):
        """List all should return items ordered by created_at DESC."""
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        w1 = WorkerDO(id="w1", type="claudecode", created_at=now - timedelta(hours=1))
        w2 = WorkerDO(id="w2", type="claudecode", created_at=now)
        repo.create(w1)
        repo.create(w2)

        results = repo.list_all()
        assert len(results) == 2
        assert results[0].id == "w2"
        assert results[1].id == "w1"

    def test_delete(self, repo):
        """Deleting should make get return None."""
        repo.create(WorkerDO(id="w1", type="claudecode"))
        assert repo.delete("w1") is True
        assert repo.get("w1") is None

    def test_create_duplicate(self, repo):
        """Inserting duplicate id should return False."""
        repo.create(WorkerDO(id="w1", type="claudecode"))
        assert repo.create(WorkerDO(id="w1", type="claudecode")) is False
