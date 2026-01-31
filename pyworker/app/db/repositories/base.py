"""Base repository class."""

import duckdb
from ...utils.logger import get_app_logger


class BaseRepository:
    """Base class for all repositories."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """
        Initialize repository with database connection.

        Args:
            conn: DuckDB connection instance
        """
        self.conn = conn
        self.logger = get_app_logger()
