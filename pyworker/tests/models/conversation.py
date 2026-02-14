"""Tests for Conversation Pydantic models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.conversation import (
    ConversationResponse,
    CreateConversationRequest,
    RenameConversationRequest,
    CreateInputRequest,
)


class TestConversationResponse:
    """SUT: ConversationResponse"""

    def test_datetime_serialization(self):
        """datetime fields should serialize to ISO format."""
        now = datetime(2025, 1, 15, 10, 30, 0)
        resp = ConversationResponse(
            id="c1", worker_name="w1", project_path="/tmp",
            created_at=now, last_activity=now
        )
        data = resp.model_dump(mode="json")
        assert "2025-01-15" in data["created_at"]


class TestCreateConversationRequest:
    """SUT: CreateConversationRequest"""

    def test_project_path_min_length(self):
        """project_path cannot be empty."""
        with pytest.raises(ValidationError):
            CreateConversationRequest(
                worker_name="w1", project_path=""
            )


class TestRenameConversationRequest:
    """SUT: RenameConversationRequest"""

    def test_new_name_max_length(self):
        """new_name exceeding 200 chars should fail."""
        with pytest.raises(ValidationError):
            RenameConversationRequest(new_name="x" * 201)


class TestCreateInputRequest:
    """SUT: CreateInputRequest"""

    def test_content_min_length(self):
        """content cannot be empty."""
        with pytest.raises(ValidationError):
            CreateInputRequest(role="user", content="")
