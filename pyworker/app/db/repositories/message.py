"""Message repository for database operations."""

import json
from typing import Optional, List
from .base import BaseRepository
from ..database_models.message import MessageDO


class MessageRepository(BaseRepository):
    """Repository for Message CRUD operations."""

    def add(self, message: MessageDO) -> Optional[int]:
        """
        Add a new message.

        Args:
            message: MessageDO instance

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            result = self.conn.execute("""
                INSERT INTO messages (id, conversation_id, worker_id, role, content, timestamp, metadata)
                VALUES (nextval('messages_id_seq'), ?, ?, ?, ?, ?, ?)
                RETURNING id
            """, [
                message.conversation_id,
                message.worker_id,
                message.role,
                message.content,
                message.timestamp,
                json.dumps(message.metadata)
            ]).fetchone()

            message_id = result[0] if result else None
            if message_id:
                self.conn.commit()
                self.logger.debug(f"Added message {message_id} to conversation {message.conversation_id}")
            return message_id
        except Exception as e:
            self.logger.error(f"Failed to add message: {e}")
            return None

    def get_by_conversation(self, conversation_id: str, limit: int = 100) -> List[MessageDO]:
        """
        Get messages for a conversation.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return

        Returns:
            List of MessageDO instances (chronological order)
        """
        try:
            results = self.conn.execute("""
                SELECT id, conversation_id, worker_id, role, content, timestamp, metadata
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, [conversation_id, limit]).fetchall()

            messages = [
                MessageDO(
                    id=row[0],
                    conversation_id=row[1],
                    worker_id=row[2],
                    role=row[3],
                    content=row[4],
                    timestamp=row[5],
                    metadata=json.loads(row[6]) if row[6] else {}
                )
                for row in results
            ]

            # Reverse to get chronological order
            messages.reverse()
            return messages
        except Exception as e:
            self.logger.error(f"Failed to get conversation messages: {e}")
            return []

    def get_by_worker(self, worker_id: str, limit: int = 100) -> List[MessageDO]:
        """
        Get recent messages for a worker.

        Args:
            worker_id: Worker ID
            limit: Maximum number of messages to return

        Returns:
            List of MessageDO instances (chronological order)
        """
        try:
            results = self.conn.execute("""
                SELECT id, conversation_id, worker_id, role, content, timestamp, metadata
                FROM messages
                WHERE worker_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, [worker_id, limit]).fetchall()

            messages = [
                MessageDO(
                    id=row[0],
                    conversation_id=row[1],
                    worker_id=row[2],
                    role=row[3],
                    content=row[4],
                    timestamp=row[5],
                    metadata=json.loads(row[6]) if row[6] else {}
                )
                for row in results
            ]

            # Reverse to get chronological order
            messages.reverse()
            return messages
        except Exception as e:
            self.logger.error(f"Failed to get worker messages: {e}")
            return []
