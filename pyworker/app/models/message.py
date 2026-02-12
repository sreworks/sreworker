"""Message API models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """
    Response model for a message.

    Abstract model that can represent different message types from various
    code tools (Claude Code, OpenCode, etc.)
    """

    id: Optional[int] = Field(None, description="Message ID")
    message_type: str = Field(description="Message type (user, assistant, queue-operation, system, etc.)")
    uuid: str = Field(description="Source's unique identifier for this message")
    content: Dict[str, Any] = Field(description="Message content (structure varies by type)")
    timestamp: datetime = Field(description="Message timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationMessagesResponse(BaseModel):
    """Response model for conversation messages."""

    conversation_id: str = Field(description="Conversation ID")
    messages: List[MessageResponse] = Field(description="List of messages")
    total: int = Field(description="Total number of messages")


class SyncMessagesResponse(BaseModel):
    """Response model for sync messages operation."""

    conversation_id: str = Field(description="Conversation ID")
    synced_count: int = Field(description="Number of new messages synced")
    total_messages: int = Field(description="Total messages in conversation after sync")
