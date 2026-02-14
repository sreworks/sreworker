"""Tests for ConversationDO dataclass."""

from datetime import datetime

from app.db.database_models.conversation import ConversationDO


class TestConversationDO:
    """Tests for ConversationDO."""

    def test_default_values(self):
        """created_at and last_activity should be auto-assigned."""
        before = datetime.utcnow()
        conv = ConversationDO(id="c1", worker_id="w1", project_path="/tmp")
        after = datetime.utcnow()

        assert before <= conv.created_at <= after
        assert before <= conv.last_activity <= after
        assert conv.is_current is False
        assert conv.metadata == {}

    def test_optional_fields(self):
        """name and raw_conversation_id should default to None."""
        conv = ConversationDO(id="c1", worker_id="w1", project_path="/tmp")
        assert conv.name is None
        assert conv.raw_conversation_id is None
