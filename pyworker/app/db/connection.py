"""Database connection and schema management."""

import duckdb
from typing import Optional
from pathlib import Path
from ..utils.logger import get_app_logger


class DatabaseConnection:
    """DuckDB connection manager."""

    def __init__(self, db_path: str = "./data/worker_manager.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.logger = get_app_logger()
        self.conn: Optional[duckdb.DuckDBPyConnection] = None

        # Ensure database directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self._connect()
        self._init_schema()

    def _connect(self):
        """Connect to DuckDB database."""
        try:
            self.conn = duckdb.connect(self.db_path)
            self.logger.info(f"Connected to DuckDB at {self.db_path}")
        except Exception as e:
            self.logger.error(f"Failed to connect to DuckDB: {e}")
            raise

    def _init_schema(self):
        """Initialize database schema."""
        try:
            # Workers table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS workers (
                    id VARCHAR PRIMARY KEY,
                    type VARCHAR NOT NULL,
                    env_vars JSON,
                    command_params JSON,
                    created_at TIMESTAMP NOT NULL
                )
            """)

            # Conversations table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id VARCHAR PRIMARY KEY,
                    worker_id VARCHAR NOT NULL,
                    project_path VARCHAR NOT NULL,
                    name VARCHAR,
                    created_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP NOT NULL,
                    is_current BOOLEAN DEFAULT FALSE,
                    raw_conversation_id VARCHAR,
                    metadata JSON
                )
            """)

            # Migration: add raw_conversation_id column if not exists
            try:
                self.conn.execute("""
                    ALTER TABLE conversations ADD COLUMN IF NOT EXISTS raw_conversation_id VARCHAR
                """)
            except Exception:
                pass  # Column already exists or table doesn't support ALTER

            # Messages table - abstract model for different code tools
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGINT PRIMARY KEY,
                    conversation_id VARCHAR NOT NULL,
                    worker_id VARCHAR NOT NULL,
                    message_type VARCHAR NOT NULL,
                    uuid VARCHAR NOT NULL,
                    content JSON NOT NULL,
                    timestamp TIMESTAMP NOT NULL
                )
            """)

            # Add unique constraint on uuid to prevent duplicate syncing
            try:
                self.conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_uuid ON messages(uuid)
                """)
            except Exception:
                pass  # Index already exists

            # Create indexes
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_workers_type ON workers(type)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_worker ON conversations(worker_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_project ON conversations(project_path)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_current ON conversations(worker_id, is_current)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_worker ON messages(worker_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")

            # Create sequence for message IDs
            self.conn.execute("CREATE SEQUENCE IF NOT EXISTS messages_id_seq START 1")

            self.logger.info("Database schema initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database schema: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
