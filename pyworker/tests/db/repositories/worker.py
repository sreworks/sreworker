"""Tests for WorkerRepository."""

import pytest
from datetime import datetime, timedelta

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
    """Tests for WorkerRepository."""

    class TestCreate:
        """SUT: WorkerRepository.create"""

        def test_returns_true(self, repo):
            """create() should return True on success."""
            worker = WorkerDO(
                id="w1", type="claudecode",
                env_vars={"KEY": "val"},
                command_params=["--verbose"]
            )
            assert repo.create(worker) is True

        def test_fields_persisted(self, repo):
            """Created worker should be retrievable with all fields."""
            worker = WorkerDO(
                id="w1", type="claudecode",
                env_vars={"KEY": "val"},
                command_params=["--verbose"]
            )
            repo.create(worker)
            result = repo.get("w1")
            assert result is not None
            assert result.id == "w1"
            assert result.type == "claudecode"
            assert result.env_vars == {"KEY": "val"}
            assert result.command_params == ["--verbose"]

        def test_duplicate_returns_false(self, repo):
            """Inserting duplicate id should return False."""
            repo.create(WorkerDO(id="w1", type="claudecode"))
            assert repo.create(WorkerDO(id="w1", type="claudecode")) is False

    class TestGet:
        """SUT: WorkerRepository.get"""

        def test_found(self, repo):
            """get() should return the worker when it exists."""
            repo.create(WorkerDO(id="w1", type="claudecode"))
            result = repo.get("w1")
            assert result is not None
            assert result.id == "w1"

        def test_not_found(self, repo):
            """get() should return None for non-existent id."""
            assert repo.get("nonexistent") is None

    class TestListAll:
        """SUT: WorkerRepository.list_all"""

        def test_ordered_by_created_at_desc(self, repo):
            """Results should be ordered by created_at DESC."""
            now = datetime.utcnow()
            w1 = WorkerDO(id="w1", type="claudecode", created_at=now - timedelta(hours=1))
            w2 = WorkerDO(id="w2", type="claudecode", created_at=now)
            repo.create(w1)
            repo.create(w2)

            results = repo.list_all()
            assert len(results) == 2
            assert results[0].id == "w2"
            assert results[1].id == "w1"

    class TestDelete:
        """SUT: WorkerRepository.delete"""

        def test_returns_true(self, repo):
            """delete() should return True on success."""
            repo.create(WorkerDO(id="w1", type="claudecode"))
            assert repo.delete("w1") is True

        def test_removes_worker(self, repo):
            """Deleted worker should not be retrievable."""
            repo.create(WorkerDO(id="w1", type="claudecode"))
            repo.delete("w1")
            assert repo.get("w1") is None
