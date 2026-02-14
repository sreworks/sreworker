"""Tests for database connection and schema management."""

import os
import shutil
import pytest
from pathlib import Path

from app.db.connection import DatabaseConnection


TEST_DB_DIR = "./data/test/db_conn"


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test.db")


class TestDatabaseConnection:
    """Tests for DatabaseConnection."""

    def test_connect_creates_file(self, db_path):
        """After connecting, the db file should exist."""
        conn = DatabaseConnection(db_path)
        assert Path(db_path).exists()
        conn.close()

    def test_schema_workers_table(self, db_path):
        """Workers table should be queryable after init."""
        conn = DatabaseConnection(db_path)
        result = conn.conn.execute("SELECT COUNT(*) FROM workers").fetchone()
        assert result[0] == 0
        conn.close()

    def test_schema_conversations_table(self, db_path):
        """Conversations table should be queryable after init."""
        conn = DatabaseConnection(db_path)
        result = conn.conn.execute("SELECT COUNT(*) FROM conversations").fetchone()
        assert result[0] == 0
        conn.close()

    def test_schema_indexes_exist(self, db_path):
        """Expected indexes should exist."""
        conn = DatabaseConnection(db_path)
        result = conn.conn.execute(
            "SELECT index_name FROM duckdb_indexes()"
        ).fetchall()
        index_names = [r[0] for r in result]
        assert "idx_workers_type" in index_names
        assert "idx_conversations_worker" in index_names
        assert "idx_conversations_project" in index_names
        conn.close()

    def test_migration_raw_conversation_id(self, db_path):
        """ALTER TABLE for raw_conversation_id should be idempotent."""
        conn = DatabaseConnection(db_path)
        # Calling _init_schema again should not raise
        conn._init_schema()
        conn.close()

    def test_context_manager(self, db_path):
        """Context manager should auto-close connection."""
        with DatabaseConnection(db_path) as conn:
            conn.conn.execute("SELECT 1").fetchone()
        # After exiting, connection should be closed

    def test_close(self, db_path):
        """After close, connection should not be usable."""
        conn = DatabaseConnection(db_path)
        conn.close()
        with pytest.raises(Exception):
            conn.conn.execute("SELECT 1")
