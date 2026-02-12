"""Conversation file storage service.

Stores messages in JSONL files with structure:
  data/conversations/{worker_name}/{uuid[:2]}/{uuid}.jsonl
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..utils import read_last_n_lines


class ConversationManager:
    """File-based conversation message storage."""

    def __init__(self, base_path: str = "./data/conversations"):
        self.base_path = Path(base_path)

    def _get_conversation_path(self, worker_name: str, conversation_id: str) -> Path:
        """Get the file path for a conversation's inputs."""
        prefix = conversation_id[:2]
        return self.base_path / worker_name / prefix / f"{conversation_id}.input.jsonl"

    def _ensure_dir(self, file_path: Path) -> None:
        """Ensure the directory exists."""
        file_path.parent.mkdir(parents=True, exist_ok=True)

    def add_input(
        self,
        worker_name: str,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add an input to a conversation.

        Args:
            worker_name: Worker name
            conversation_id: Conversation ID
            role: Input role (user/assistant)
            content: Input content
            metadata: Optional metadata

        Returns:
            The input record that was added
        """
        file_path = self._get_conversation_path(worker_name, conversation_id)
        self._ensure_dir(file_path)

        input_record = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(input_record, ensure_ascii=False) + "\n")

        return input_record

    def get_inputs(
        self,
        worker_name: str,
        conversation_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get inputs from a conversation.

        Memory efficient - only reads the last N lines from file.

        Args:
            worker_name: Worker name
            conversation_id: Conversation ID
            limit: Maximum number of inputs to return

        Returns:
            List of inputs (chronological order, oldest first)
        """
        file_path = self._get_conversation_path(worker_name, conversation_id)

        if not file_path.exists():
            return []

        # Read last N lines efficiently (returns in chronological order)
        lines = read_last_n_lines(file_path, limit)

        return [json.loads(line) for line in lines if line.strip()]

    def delete_conversation(self, worker_name: str, conversation_id: str) -> bool:
        """
        Delete a conversation's message file.

        Args:
            worker_name: Worker name
            conversation_id: Conversation ID

        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_conversation_path(worker_name, conversation_id)

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def conversation_exists(self, worker_name: str, conversation_id: str) -> bool:
        """Check if a conversation file exists."""
        file_path = self._get_conversation_path(worker_name, conversation_id)
        return file_path.exists()
