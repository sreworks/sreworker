"""Tests for ClaudeCodeWorker."""

import json
import pytest
from datetime import datetime
from pathlib import Path

from app.workers.v1.claude import ClaudeCodeWorker
from app.models.message import MessageResponse, MessageContent


@pytest.fixture(autouse=True)
def cleanup_class_state():
    """Reset ClaudeCodeWorker class-level state after each test."""
    yield
    ClaudeCodeWorker._active_sessions.clear()
    ClaudeCodeWorker._file_manager = None
    ClaudeCodeWorker._conv_manager_ref = None
    ClaudeCodeWorker._watching = False


class TestConvertRawMessage:
    """Tests for _convert_raw_message (pure logic, no IO)."""

    def _make_worker(self):
        return ClaudeCodeWorker()

    def test_convert_user_text_message(self):
        """User message with string content."""
        worker = self._make_worker()
        raw = {
            "type": "user",
            "uuid": "u1",
            "timestamp": "2025-01-01T12:00:00Z",
            "message": {"content": "hello world"}
        }
        msg = worker._convert_raw_message(raw)
        assert msg.type == "user"
        assert len(msg.contents) == 1
        assert msg.contents[0].type == "text"
        assert msg.contents[0].content == "hello world"

    def test_convert_user_list_content(self):
        """User message with list content blocks."""
        worker = self._make_worker()
        raw = {
            "type": "user",
            "uuid": "u2",
            "timestamp": "2025-01-01T12:00:00Z",
            "message": {
                "content": [
                    {"type": "text", "text": "some text"},
                    {"type": "tool_result", "content": "result", "tool_use_id": "tool1"}
                ]
            }
        }
        msg = worker._convert_raw_message(raw)
        assert len(msg.contents) == 2
        assert msg.contents[0].type == "text"
        assert msg.contents[0].content == "some text"
        assert msg.contents[1].type == "tool_result"
        assert msg.contents[1].tool_name == "tool1"

    def test_convert_assistant_text(self):
        """Assistant message with text block."""
        worker = self._make_worker()
        raw = {
            "type": "assistant",
            "uuid": "a1",
            "timestamp": "2025-01-01T12:00:00Z",
            "message": {
                "content": [{"type": "text", "text": "I can help"}],
                "model": "claude-3",
                "usage": {"input_tokens": 10, "output_tokens": 20}
            }
        }
        msg = worker._convert_raw_message(raw)
        assert msg.type == "assistant"
        assert msg.contents[0].content == "I can help"
        assert msg.model == "claude-3"
        assert msg.usage["input_tokens"] == 10

    def test_convert_assistant_tool_use(self):
        """Assistant message with tool_use block."""
        worker = self._make_worker()
        raw = {
            "type": "assistant",
            "uuid": "a2",
            "timestamp": "2025-01-01T12:00:00Z",
            "message": {
                "content": [{
                    "type": "tool_use",
                    "name": "read_file",
                    "input": {"path": "/tmp/test.py"}
                }]
            }
        }
        msg = worker._convert_raw_message(raw)
        assert msg.contents[0].type == "tool_use"
        assert msg.contents[0].tool_name == "read_file"
        assert "path" in msg.contents[0].content

    def test_convert_assistant_tool_result(self):
        """Assistant message with tool_result block."""
        worker = self._make_worker()
        raw = {
            "type": "assistant",
            "uuid": "a3",
            "timestamp": "2025-01-01T12:00:00Z",
            "message": {
                "content": [{
                    "type": "tool_result",
                    "content": "file contents here",
                    "tool_use_id": "tool123"
                }]
            }
        }
        msg = worker._convert_raw_message(raw)
        assert msg.contents[0].type == "tool_result"
        assert msg.contents[0].content == "file contents here"
        assert msg.contents[0].tool_name == "tool123"

    def test_convert_assistant_error(self):
        """Assistant message with error field."""
        worker = self._make_worker()
        raw = {
            "type": "assistant",
            "uuid": "a4",
            "timestamp": "2025-01-01T12:00:00Z",
            "message": {
                "content": [],
                "error": "rate limit exceeded"
            }
        }
        msg = worker._convert_raw_message(raw)
        assert msg.error == "rate limit exceeded"

    def test_convert_unknown_type(self):
        """Unknown type should produce empty contents list."""
        worker = self._make_worker()
        raw = {
            "type": "queue-operation",
            "uuid": "q1",
            "timestamp": "2025-01-01T12:00:00Z",
            "message": {}
        }
        msg = worker._convert_raw_message(raw)
        assert msg.type == "queue-operation"
        assert msg.contents == []

    def test_convert_missing_timestamp(self):
        """Missing timestamp should fallback to utcnow."""
        worker = self._make_worker()
        before = datetime.utcnow()
        raw = {"type": "user", "uuid": "u3", "message": {"content": "hi"}}
        msg = worker._convert_raw_message(raw)
        after = datetime.utcnow()
        assert before <= msg.timestamp <= after


class TestFetchMessages:
    """Tests for fetch_messages (mock file system)."""

    @pytest.mark.asyncio
    async def test_fetch_messages_file_not_found(self):
        """Non-existent session should return empty list."""
        worker = ClaudeCodeWorker()
        result = await worker.fetch_messages("nonexistent-session-id")
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_messages_reads_jsonl(self, tmp_path, monkeypatch):
        """Should parse JSONL file into MessageResponse list."""
        session_id = "test-session"
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        session_file = project_dir / f"{session_id}.jsonl"

        lines = [
            json.dumps({
                "type": "user", "uuid": "u1",
                "timestamp": "2025-01-01T12:00:00Z",
                "message": {"content": "hello"}
            }),
            json.dumps({
                "type": "assistant", "uuid": "a1",
                "timestamp": "2025-01-01T12:00:01Z",
                "message": {"content": [{"type": "text", "text": "hi"}]}
            })
        ]
        session_file.write_text("\n".join(lines) + "\n")

        worker = ClaudeCodeWorker()
        monkeypatch.setattr(worker, "_find_session_file", lambda sid: session_file)

        result = await worker.fetch_messages(session_id)
        assert len(result) == 2
        assert result[0].type == "user"
        assert result[1].type == "assistant"

    @pytest.mark.asyncio
    async def test_fetch_messages_skips_invalid_json(self, tmp_path, monkeypatch):
        """Bad lines should be skipped without error."""
        session_id = "test-session"
        session_file = tmp_path / f"{session_id}.jsonl"
        lines = [
            "not valid json",
            json.dumps({
                "type": "user", "uuid": "u1",
                "timestamp": "2025-01-01T12:00:00Z",
                "message": {"content": "hello"}
            })
        ]
        session_file.write_text("\n".join(lines) + "\n")

        worker = ClaudeCodeWorker()
        monkeypatch.setattr(worker, "_find_session_file", lambda sid: session_file)

        result = await worker.fetch_messages(session_id)
        assert len(result) == 1


class TestSessionManagement:
    """Tests for class-level session state."""

    def test_activate_deactivate_session(self):
        """activate/deactivate should add/remove from _active_sessions."""
        ClaudeCodeWorker.activate_session("raw1", "conv1", "w1")
        assert "raw1" in ClaudeCodeWorker._active_sessions

        ClaudeCodeWorker.deactivate_session("raw1")
        assert "raw1" not in ClaudeCodeWorker._active_sessions

    def test_stop_watching_clears_state(self):
        """stop_watching should clear all class-level state."""
        ClaudeCodeWorker._active_sessions["raw1"] = ("conv1", "w1")
        ClaudeCodeWorker._watching = True

        ClaudeCodeWorker.stop_watching()

        assert ClaudeCodeWorker._active_sessions == {}
        assert ClaudeCodeWorker._file_manager is None
        assert ClaudeCodeWorker._conv_manager_ref is None
        assert ClaudeCodeWorker._watching is False
