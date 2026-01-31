"""DuckDB database management service - V1"""

import duckdb
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import json
from ...utils.logger import get_app_logger


class DatabaseManager:
    """DuckDB database manager for persistent storage"""

    def __init__(self, db_path: str = "./data/worker_manager.db"):
        """
        Initialize database manager

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.logger = get_app_logger()

        # Ensure database directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Initialize connection
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self._connect()
        self._init_schema()

    def _connect(self):
        """Connect to DuckDB database"""
        try:
            self.conn = duckdb.connect(self.db_path)
            self.logger.info(f"Connected to DuckDB at {self.db_path}")
        except Exception as e:
            self.logger.error(f"Failed to connect to DuckDB: {e}")
            raise

    def _init_schema(self):
        """Initialize database schema"""
        try:
            # Workers table (project_path removed - it belongs to conversation)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS workers (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    ai_cli_type VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    config JSON,
                    created_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP,
                    INDEX idx_workers_status (status),
                    INDEX idx_workers_ai_cli_type (ai_cli_type)
                )
            """)

            # Conversations table (project_path added here)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id VARCHAR PRIMARY KEY,
                    worker_id VARCHAR NOT NULL,
                    project_path VARCHAR NOT NULL,
                    name VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP NOT NULL,
                    is_current BOOLEAN DEFAULT FALSE,
                    metadata JSON,
                    INDEX idx_conversations_worker (worker_id),
                    INDEX idx_conversations_project (project_path),
                    INDEX idx_conversations_current (worker_id, is_current),
                    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE
                )
            """)

            # Messages table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGINT PRIMARY KEY,
                    conversation_id VARCHAR NOT NULL,
                    worker_id VARCHAR NOT NULL,
                    role VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata JSON,
                    INDEX idx_messages_conversation (conversation_id),
                    INDEX idx_messages_worker (worker_id),
                    INDEX idx_messages_timestamp (timestamp),
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE
                )
            """)

            # Create sequence for message IDs
            self.conn.execute("""
                CREATE SEQUENCE IF NOT EXISTS messages_id_seq START 1
            """)

            self.logger.info("Database schema initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database schema: {e}")
            raise

    # === Worker CRUD Operations ===

    def create_worker(self, worker_data: Dict[str, Any]) -> bool:
        """
        Create a new worker record

        Args:
            worker_data: Worker data dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            self.conn.execute("""
                INSERT INTO workers (id, name, ai_cli_type, status, config, created_at, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                worker_data['id'],
                worker_data['name'],
                worker_data['ai_cli_type'],
                worker_data['status'],
                json.dumps(worker_data.get('config', {})),
                worker_data['created_at'],
                worker_data.get('last_activity')
            ])
            self.logger.info(f"Created worker record: {worker_data['id']}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create worker: {e}")
            return False

    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Get worker by ID

        Args:
            worker_id: Worker ID

        Returns:
            Worker data dictionary or None
        """
        try:
            result = self.conn.execute("""
                SELECT id, name, ai_cli_type, status, config, created_at, last_activity
                FROM workers
                WHERE id = ?
            """, [worker_id]).fetchone()

            if result:
                return {
                    'id': result[0],
                    'name': result[1],
                    'ai_cli_type': result[2],
                    'status': result[3],
                    'config': json.loads(result[4]) if result[4] else {},
                    'created_at': result[5],
                    'last_activity': result[6]
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get worker {worker_id}: {e}")
            return None

    def list_workers(self) -> List[Dict[str, Any]]:
        """
        List all workers

        Returns:
            List of worker data dictionaries
        """
        try:
            results = self.conn.execute("""
                SELECT id, name, ai_cli_type, status, config, created_at, last_activity
                FROM workers
                ORDER BY created_at DESC
            """).fetchall()

            workers = []
            for row in results:
                workers.append({
                    'id': row[0],
                    'name': row[1],
                    'ai_cli_type': row[2],
                    'status': row[3],
                    'config': json.loads(row[4]) if row[4] else {},
                    'created_at': row[5],
                    'last_activity': row[6]
                })
            return workers
        except Exception as e:
            self.logger.error(f"Failed to list workers: {e}")
            return []

    def update_worker_status(self, worker_id: str, status: str, last_activity: Optional[datetime] = None) -> bool:
        """
        Update worker status

        Args:
            worker_id: Worker ID
            status: New status
            last_activity: Last activity timestamp

        Returns:
            True if successful, False otherwise
        """
        try:
            if last_activity is None:
                last_activity = datetime.utcnow()

            self.conn.execute("""
                UPDATE workers
                SET status = ?, last_activity = ?
                WHERE id = ?
            """, [status, last_activity, worker_id])
            return True
        except Exception as e:
            self.logger.error(f"Failed to update worker status: {e}")
            return False

    def delete_worker(self, worker_id: str) -> bool:
        """
        Delete worker

        Args:
            worker_id: Worker ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.conn.execute("DELETE FROM workers WHERE id = ?", [worker_id])
            self.logger.info(f"Deleted worker record: {worker_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete worker: {e}")
            return False

    # === Conversation CRUD Operations ===

    def create_conversation(self, conversation_data: Dict[str, Any]) -> bool:
        """
        Create a new conversation record

        Args:
            conversation_data: Conversation data dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            # Unset current conversation for this worker
            if conversation_data.get('is_current', False):
                self.conn.execute("""
                    UPDATE conversations
                    SET is_current = FALSE
                    WHERE worker_id = ?
                """, [conversation_data['worker_id']])

            self.conn.execute("""
                INSERT INTO conversations (id, worker_id, project_path, name, created_at, last_activity, is_current, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                conversation_data['id'],
                conversation_data['worker_id'],
                conversation_data['project_path'],
                conversation_data['name'],
                conversation_data['created_at'],
                conversation_data['last_activity'],
                conversation_data.get('is_current', False),
                json.dumps(conversation_data.get('metadata', {}))
            ])
            self.logger.info(f"Created conversation record: {conversation_data['id']}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {e}")
            return False

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation by ID

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation data dictionary or None
        """
        try:
            result = self.conn.execute("""
                SELECT id, worker_id, project_path, name, created_at, last_activity, is_current, metadata
                FROM conversations
                WHERE id = ?
            """, [conversation_id]).fetchone()

            if result:
                return {
                    'id': result[0],
                    'worker_id': result[1],
                    'project_path': result[2],
                    'name': result[3],
                    'created_at': result[4],
                    'last_activity': result[5],
                    'is_current': result[6],
                    'metadata': json.loads(result[7]) if result[7] else {}
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None

    def list_conversations(self, worker_id: str) -> List[Dict[str, Any]]:
        """
        List conversations for a worker

        Args:
            worker_id: Worker ID

        Returns:
            List of conversation data dictionaries
        """
        try:
            results = self.conn.execute("""
                SELECT id, worker_id, project_path, name, created_at, last_activity, is_current, metadata
                FROM conversations
                WHERE worker_id = ?
                ORDER BY last_activity DESC
            """, [worker_id]).fetchall()

            conversations = []
            for row in results:
                conversations.append({
                    'id': row[0],
                    'worker_id': row[1],
                    'project_path': row[2],
                    'name': row[3],
                    'created_at': row[4],
                    'last_activity': row[5],
                    'is_current': row[6],
                    'metadata': json.loads(row[7]) if row[7] else {}
                })
            return conversations
        except Exception as e:
            self.logger.error(f"Failed to list conversations: {e}")
            return []

    def get_current_conversation(self, worker_id: str) -> Optional[str]:
        """
        Get current conversation ID for a worker

        Args:
            worker_id: Worker ID

        Returns:
            Current conversation ID or None
        """
        try:
            result = self.conn.execute("""
                SELECT id
                FROM conversations
                WHERE worker_id = ? AND is_current = TRUE
                LIMIT 1
            """, [worker_id]).fetchone()

            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get current conversation: {e}")
            return None

    def switch_conversation(self, worker_id: str, conversation_id: str) -> bool:
        """
        Switch current conversation

        Args:
            worker_id: Worker ID
            conversation_id: Conversation ID to switch to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Unset all current conversations for this worker
            self.conn.execute("""
                UPDATE conversations
                SET is_current = FALSE
                WHERE worker_id = ?
            """, [worker_id])

            # Set new current conversation
            self.conn.execute("""
                UPDATE conversations
                SET is_current = TRUE, last_activity = ?
                WHERE id = ? AND worker_id = ?
            """, [datetime.utcnow(), conversation_id, worker_id])

            return True
        except Exception as e:
            self.logger.error(f"Failed to switch conversation: {e}")
            return False

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation

        Args:
            conversation_id: Conversation ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.conn.execute("DELETE FROM conversations WHERE id = ?", [conversation_id])
            self.logger.info(f"Deleted conversation record: {conversation_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete conversation: {e}")
            return False

    def update_conversation(self, conversation_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update conversation fields

        Args:
            conversation_id: Conversation ID
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            set_clauses = []
            params = []

            if 'name' in updates:
                set_clauses.append("name = ?")
                params.append(updates['name'])

            if 'last_activity' in updates:
                set_clauses.append("last_activity = ?")
                params.append(updates['last_activity'])

            if 'metadata' in updates:
                set_clauses.append("metadata = ?")
                params.append(json.dumps(updates['metadata']))

            if not set_clauses:
                return True

            params.append(conversation_id)
            query = f"UPDATE conversations SET {', '.join(set_clauses)} WHERE id = ?"

            self.conn.execute(query, params)
            return True
        except Exception as e:
            self.logger.error(f"Failed to update conversation: {e}")
            return False

    # === Message CRUD Operations ===

    def add_message(self, message_data: Dict[str, Any]) -> Optional[int]:
        """
        Add a message

        Args:
            message_data: Message data dictionary

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            result = self.conn.execute("""
                INSERT INTO messages (id, conversation_id, worker_id, role, content, timestamp, metadata)
                VALUES (nextval('messages_id_seq'), ?, ?, ?, ?, ?, ?)
                RETURNING id
            """, [
                message_data['conversation_id'],
                message_data['worker_id'],
                message_data['role'],
                message_data['content'],
                message_data['timestamp'],
                json.dumps(message_data.get('metadata', {}))
            ]).fetchone()

            message_id = result[0] if result else None
            if message_id:
                self.logger.debug(f"Added message {message_id} to conversation {message_data['conversation_id']}")
            return message_id
        except Exception as e:
            self.logger.error(f"Failed to add message: {e}")
            return None

    def get_conversation_messages(self, conversation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        try:
            results = self.conn.execute("""
                SELECT id, conversation_id, worker_id, role, content, timestamp, metadata
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, [conversation_id, limit]).fetchall()

            messages = []
            for row in results:
                messages.append({
                    'id': row[0],
                    'conversation_id': row[1],
                    'worker_id': row[2],
                    'role': row[3],
                    'content': row[4],
                    'timestamp': row[5],
                    'metadata': json.loads(row[6]) if row[6] else {}
                })

            # Reverse to get chronological order
            messages.reverse()
            return messages
        except Exception as e:
            self.logger.error(f"Failed to get conversation messages: {e}")
            return []

    def get_worker_messages(self, worker_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent messages for a worker

        Args:
            worker_id: Worker ID
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        try:
            results = self.conn.execute("""
                SELECT id, conversation_id, worker_id, role, content, timestamp, metadata
                FROM messages
                WHERE worker_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, [worker_id, limit]).fetchall()

            messages = []
            for row in results:
                messages.append({
                    'id': row[0],
                    'conversation_id': row[1],
                    'worker_id': row[2],
                    'role': row[3],
                    'content': row[4],
                    'timestamp': row[5],
                    'metadata': json.loads(row[6]) if row[6] else {}
                })

            # Reverse to get chronological order
            messages.reverse()
            return messages
        except Exception as e:
            self.logger.error(f"Failed to get worker messages: {e}")
            return []

    # === Utility Methods ===

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
