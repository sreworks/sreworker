"""Tests for WorkerDO dataclass."""

from datetime import datetime

from app.db.database_models.worker import WorkerDO


class TestWorkerDO:
    """Tests for WorkerDO."""

    def test_default_values(self):
        """env_vars, command_params, and created_at should have defaults."""
        before = datetime.utcnow()
        worker = WorkerDO(id="w1", type="claudecode")
        after = datetime.utcnow()

        assert worker.env_vars == {}
        assert worker.command_params == []
        assert before <= worker.created_at <= after

    def test_required_fields(self):
        """id and type are required."""
        worker = WorkerDO(id="w1", type="claudecode")
        assert worker.id == "w1"
        assert worker.type == "claudecode"
