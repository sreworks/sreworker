"""Tests for BaseRepository."""

from unittest.mock import MagicMock

from app.db.repositories.base import BaseRepository


class TestBaseRepository:
    """Tests for BaseRepository."""

    def test_init_stores_conn(self):
        """conn attribute should be correctly assigned."""
        mock_conn = MagicMock()
        repo = BaseRepository(mock_conn)
        assert repo.conn is mock_conn

    def test_init_has_logger(self):
        """logger attribute should exist."""
        mock_conn = MagicMock()
        repo = BaseRepository(mock_conn)
        assert repo.logger is not None
