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
                INSERT INTO messages (id, conversation_id, worker_id, message_type, uuid, content, timestamp)
                VALUES (nextval('messages_id_seq'), ?, ?, ?, ?, ?, ?)
                RETURNING id
            """, [
                message.conversation_id,
                message.worker_id,
                message.message_type,
                message.uuid,
                json.dumps(message.content),
                message.timestamp
            ]).fetchone()

            message_id = result[0] if result else None
            if message_id:
                self.conn.commit()
                self.logger.debug(f"Added message {message_id} to conversation {message.conversation_id}")
            return message_id
        except Exception as e:
            self.logger.error(f"Failed to add message: {e}")
            return None

    def add_batch(self, messages: List[MessageDO]) -> int:
        """
        Add multiple messages in batch.

        Args:
            messages: List of MessageDO instances

        Returns:
            Number of messages successfully added
        """
        added_count = 0
        for message in messages:
            try:
                # Use INSERT OR IGNORE pattern with uuid uniqueness
                self.conn.execute("""
                    INSERT INTO messages (id, conversation_id, worker_id, message_type, uuid, content, timestamp)
                    SELECT nextval('messages_id_seq'), ?, ?, ?, ?, ?, ?
                    WHERE NOT EXISTS (SELECT 1 FROM messages WHERE uuid = ?)
                """, [
                    message.conversation_id,
                    message.worker_id,
                    message.message_type,
                    message.uuid,
                    json.dumps(message.content),
                    message.timestamp,
                    message.uuid
                ])
                added_count += 1
            except Exception as e:
                self.logger.debug(f"Skipped duplicate message {message.uuid}: {e}")

        if added_count > 0:
            self.conn.commit()
            self.logger.debug(f"Added {added_count} messages in batch")

        return added_count

    def exists_by_uuid(self, uuid: str) -> bool:
        """
        Check if a message with the given uuid exists.

        Args:
            uuid: Message UUID

        Returns:
            True if exists, False otherwise
        """
        try:
            result = self.conn.execute("""
                SELECT 1 FROM messages WHERE uuid = ? LIMIT 1
            """, [uuid]).fetchone()
            return result is not None
        except Exception as e:
            self.logger.error(f"Failed to check message existence: {e}")
            return False

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
                SELECT id, conversation_id, worker_id, message_type, uuid, content, timestamp
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
                    message_type=row[3],
                    uuid=row[4],
                    content=json.loads(row[5]) if isinstance(row[5], str) else row[5],
                    timestamp=row[6]
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
                SELECT id, conversation_id, worker_id, message_type, uuid, content, timestamp
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
                    message_type=row[3],
                    uuid=row[4],
                    content=json.loads(row[5]) if isinstance(row[5], str) else row[5],
                    timestamp=row[6]
                )
                for row in results
            ]

            # Reverse to get chronological order
            messages.reverse()
            return messages
        except Exception as e:
            self.logger.error(f"Failed to get worker messages: {e}")
            return []

    def get_latest_uuid(self, conversation_id: str) -> Optional[str]:
        """
        Get the latest message UUID for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Latest message UUID or None
        """
        try:
            result = self.conn.execute("""
                SELECT uuid FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, [conversation_id]).fetchone()
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get latest message uuid: {e}")
            return None

    def delete_by_conversation(self, conversation_id: str) -> bool:
        """
        Delete all messages for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.conn.execute("""
                DELETE FROM messages WHERE conversation_id = ?
            """, [conversation_id])
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete messages: {e}")
            return False
