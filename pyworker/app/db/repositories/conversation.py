"""Conversation repository for database operations."""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from .base import BaseRepository
from ..database_models.conversation import ConversationDO


class ConversationRepository(BaseRepository):
    """Repository for Conversation CRUD operations."""

    def create(self, conversation: ConversationDO) -> bool:
        """
        Create a new conversation record.

        Args:
            conversation: ConversationDO instance

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use string formatting to avoid prepared statement cache issues
            metadata_json = json.dumps(conversation.metadata) if conversation.metadata else '{}'
            raw_conv_id = f"'{conversation.raw_conversation_id}'" if conversation.raw_conversation_id else "NULL"

            sql = f"""
                INSERT INTO conversations (id, worker_id, project_path, name, created_at, last_activity, is_current, raw_conversation_id, metadata)
                VALUES (
                    '{conversation.id}',
                    '{conversation.worker_id}',
                    '{conversation.project_path}',
                    '{conversation.name}',
                    '{conversation.created_at.isoformat()}',
                    '{conversation.last_activity.isoformat()}',
                    {conversation.is_current},
                    {raw_conv_id},
                    '{metadata_json}'
                )
            """
            self.conn.execute(sql)
            self.conn.commit()
            self.logger.info(f"Created conversation record: {conversation.id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {e}")
            return False

    def get(self, conversation_id: str) -> Optional[ConversationDO]:
        """
        Get conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            ConversationDO instance or None
        """
        try:
            result = self.conn.execute("""
                SELECT id, worker_id, project_path, name, created_at, last_activity, is_current, raw_conversation_id, metadata
                FROM conversations
                WHERE id = ?
            """, [conversation_id]).fetchone()

            if result:
                return ConversationDO(
                    id=result[0],
                    worker_id=result[1],
                    project_path=result[2],
                    name=result[3],
                    created_at=result[4],
                    last_activity=result[5],
                    is_current=result[6],
                    raw_conversation_id=result[7],
                    metadata=json.loads(result[8]) if result[8] else {}
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None

    def list_by_worker(self, worker_id: str) -> List[ConversationDO]:
        """
        List conversations for a worker.

        Args:
            worker_id: Worker ID

        Returns:
            List of ConversationDO instances
        """
        try:
            results = self.conn.execute("""
                SELECT id, worker_id, project_path, name, created_at, last_activity, is_current, raw_conversation_id, metadata
                FROM conversations
                WHERE worker_id = ?
                ORDER BY last_activity DESC
            """, [worker_id]).fetchall()

            return [
                ConversationDO(
                    id=row[0],
                    worker_id=row[1],
                    project_path=row[2],
                    name=row[3],
                    created_at=row[4],
                    last_activity=row[5],
                    is_current=row[6],
                    raw_conversation_id=row[7],
                    metadata=json.loads(row[8]) if row[8] else {}
                )
                for row in results
            ]
        except Exception as e:
            self.logger.error(f"Failed to list conversations: {e}")
            return []

    def list_all(self) -> List[ConversationDO]:
        """
        List all conversations.

        Returns:
            List of ConversationDO instances
        """
        try:
            results = self.conn.execute("""
                SELECT id, worker_id, project_path, name, created_at, last_activity, is_current, raw_conversation_id, metadata
                FROM conversations
                ORDER BY last_activity DESC
            """).fetchall()

            return [
                ConversationDO(
                    id=row[0],
                    worker_id=row[1],
                    project_path=row[2],
                    name=row[3],
                    created_at=row[4],
                    last_activity=row[5],
                    is_current=row[6],
                    raw_conversation_id=row[7],
                    metadata=json.loads(row[8]) if row[8] else {}
                )
                for row in results
            ]
        except Exception as e:
            self.logger.error(f"Failed to list all conversations: {e}")
            return []

    def get_current(self, worker_id: str) -> Optional[str]:
        """
        Get current conversation ID for a worker.

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

    def switch_current(self, worker_id: str, conversation_id: str) -> bool:
        """
        Switch current conversation for a worker.

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

            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to switch conversation: {e}")
            return False

    def delete(self, conversation_id: str) -> bool:
        """
        Delete conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.conn.execute("DELETE FROM conversations WHERE id = ?", [conversation_id])
            self.conn.commit()
            self.logger.info(f"Deleted conversation record: {conversation_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete conversation: {e}")
            return False

    def update(self, conversation_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update conversation fields.

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

            if 'raw_conversation_id' in updates:
                set_clauses.append("raw_conversation_id = ?")
                params.append(updates['raw_conversation_id'])

            if 'metadata' in updates:
                set_clauses.append("metadata = ?")
                params.append(json.dumps(updates['metadata']))

            if not set_clauses:
                return True

            params.append(conversation_id)
            query = f"UPDATE conversations SET {', '.join(set_clauses)} WHERE id = ?"

            self.conn.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to update conversation: {e}")
            return False
