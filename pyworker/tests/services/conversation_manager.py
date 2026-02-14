"""Tests for ConversationManager service."""

import json
import pytest
from datetime import datetime

from app.services.conversation_manager import ConversationManager
from app.models.message import MessageResponse, MessageContent


@pytest.fixture
def manager(tmp_path):
    """Provide a ConversationManager with tmp_path as base."""
    return ConversationManager(str(tmp_path))


class TestConversationManager:
    """Tests for file-based conversation storage."""

    def test_add_input_creates_file(self, manager, tmp_path):
        """First write should create the directory and file."""
        manager.add_input("worker1", "conv-1234", "user", "hello")
        path = tmp_path / "worker1" / "co" / "conv-1234.input.jsonl"
        assert path.exists()

    def test_add_input_appends(self, manager):
        """Multiple writes should append lines."""
        manager.add_input("w1", "c1234567", "user", "msg1")
        manager.add_input("w1", "c1234567", "assistant", "msg2")
        inputs = manager.get_inputs("w1", "c1234567")
        assert len(inputs) == 2
        # get_inputs returns newest first (reverse order)
        assert inputs[0]["content"] == "msg2"
        assert inputs[1]["content"] == "msg1"

    def test_get_inputs_empty(self, manager):
        """File not existing should return empty list."""
        assert manager.get_inputs("w1", "nonexistent") == []

    def test_get_inputs_limit(self, manager):
        """Should only return last N inputs."""
        for i in range(10):
            manager.add_input("w1", "c1234567", "user", f"msg{i}")
        inputs = manager.get_inputs("w1", "c1234567", limit=3)
        assert len(inputs) == 3

    def test_get_inputs_reverse_order(self, manager):
        """Inputs should be in reverse chronological order (newest first)."""
        manager.add_input("w1", "c1234567", "user", "first")
        manager.add_input("w1", "c1234567", "user", "second")
        manager.add_input("w1", "c1234567", "user", "third")
        inputs = manager.get_inputs("w1", "c1234567")
        assert inputs[0]["content"] == "third"
        assert inputs[-1]["content"] == "first"

    def test_save_messages_overwrites(self, manager):
        """save_messages should overwrite existing file."""
        msgs1 = [MessageResponse(
            uuid="u1", type="user",
            contents=[MessageContent(type="text", content="old")],
            timestamp=datetime.utcnow()
        )]
        msgs2 = [MessageResponse(
            uuid="u2", type="assistant",
            contents=[MessageContent(type="text", content="new")],
            timestamp=datetime.utcnow()
        )]
        manager.save_messages("w1", "c1234567", msgs1)
        manager.save_messages("w1", "c1234567", msgs2)

        result = manager.get_messages("w1", "c1234567")
        assert len(result) == 1
        assert result[0].uuid == "u2"

    def test_save_messages_returns_count(self, manager):
        """save_messages should return the number of messages written."""
        msgs = [
            MessageResponse(
                uuid=f"u{i}", type="user",
                contents=[MessageContent(type="text", content=f"msg{i}")],
                timestamp=datetime.utcnow()
            )
            for i in range(3)
        ]
        count = manager.save_messages("w1", "c1234567", msgs)
        assert count == 3

    def test_get_messages(self, manager):
        """Saved messages should be readable as MessageResponse."""
        msgs = [MessageResponse(
            uuid="u1", type="user",
            contents=[MessageContent(type="text", content="hello")],
            timestamp=datetime(2025, 1, 1, 12, 0, 0)
        )]
        manager.save_messages("w1", "c1234567", msgs)
        result = manager.get_messages("w1", "c1234567")
        assert len(result) == 1
        assert result[0].uuid == "u1"
        assert result[0].contents[0].content == "hello"

    def test_get_messages_empty(self, manager):
        """Non-existent messages file should return empty list."""
        assert manager.get_messages("w1", "nonexistent") == []

    def test_delete_conversation(self, manager):
        """Deleting should remove both input and messages files."""
        manager.add_input("w1", "c1234567", "user", "hello")
        msgs = [MessageResponse(
            uuid="u1", type="user",
            contents=[MessageContent(type="text", content="hi")],
            timestamp=datetime.utcnow()
        )]
        manager.save_messages("w1", "c1234567", msgs)

        assert manager.delete_conversation("w1", "c1234567") is True
        assert manager.get_inputs("w1", "c1234567") == []
        assert manager.get_messages("w1", "c1234567") == []

    def test_delete_conversation_not_found(self, manager):
        """Deleting non-existent conversation should return False."""
        assert manager.delete_conversation("w1", "nonexistent") is False

    def test_conversation_exists(self, manager):
        """conversation_exists should return True after add_input."""
        assert manager.conversation_exists("w1", "c1234567") is False
        manager.add_input("w1", "c1234567", "user", "hello")
        assert manager.conversation_exists("w1", "c1234567") is True

    def test_path_structure(self, manager, tmp_path):
        """Path should follow {worker}/{uuid[:2]}/{uuid}.input.jsonl pattern."""
        conv_id = "abcdef1234567890"
        manager.add_input("myworker", conv_id, "user", "test")
        expected = tmp_path / "myworker" / "ab" / f"{conv_id}.input.jsonl"
        assert expected.exists()
