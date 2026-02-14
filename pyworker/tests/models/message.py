"""Tests for Message Pydantic models."""

import json
from datetime import datetime

from app.models.message import (
    MessageContent,
    MessageResponse,
    ConversationMessagesResponse,
    SyncMessagesResponse,
)


class TestMessageContent:
    """SUT: MessageContent"""

    def test_creation(self):
        """MessageContent should hold type and content."""
        mc = MessageContent(type="text", content="hello")
        assert mc.type == "text"
        assert mc.content == "hello"
        assert mc.tool_name is None


class TestMessageResponse:
    """SUT: MessageResponse"""

    def test_serialization(self):
        """model_dump_json() should produce valid JSON."""
        msg = MessageResponse(
            uuid="u1", type="user",
            contents=[MessageContent(type="text", content="hi")],
            timestamp=datetime(2025, 1, 1, 12, 0, 0)
        )
        data = json.loads(msg.model_dump_json())
        assert data["uuid"] == "u1"
        assert data["type"] == "user"
        assert len(data["contents"]) == 1

    def test_optional_fields(self):
        """model, usage, error should default to None."""
        msg = MessageResponse(
            uuid="u1", type="user",
            contents=[], timestamp=datetime.utcnow()
        )
        assert msg.model is None
        assert msg.usage is None
        assert msg.error is None


class TestConversationMessagesResponse:
    """SUT: ConversationMessagesResponse"""

    def test_holds_nested_messages(self):
        """Should hold nested messages with correct total."""
        msg = MessageResponse(
            uuid="u1", type="user",
            contents=[MessageContent(type="text", content="hi")],
            timestamp=datetime.utcnow()
        )
        resp = ConversationMessagesResponse(
            conversation_id="c1", messages=[msg], total=1
        )
        assert resp.total == 1
        assert len(resp.messages) == 1
        assert resp.messages[0].uuid == "u1"


class TestSyncMessagesResponse:
    """SUT: SyncMessagesResponse"""

    def test_fields(self):
        """Should have correct fields."""
        resp = SyncMessagesResponse(
            conversation_id="c1", synced_count=5, total_messages=10
        )
        assert resp.conversation_id == "c1"
        assert resp.synced_count == 5
        assert resp.total_messages == 10
