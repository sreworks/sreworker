"""Message API models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MessageContent(BaseModel):
    """Single content block within a message."""

    type: str = Field(description="Content type: text, tool_use, tool_result, error, etc.")
    content: str = Field(description="Text content / tool input JSON / error message")
    tool_name: Optional[str] = Field(None, description="Tool name (for tool_use/tool_result)")


class MessageResponse(BaseModel):
    """
    Standardized message response model.

    Provides a uniform interface across different code tools
    (Claude Code, OpenCode, etc.)
    """

    uuid: str = Field(description="Unique identifier for this message")
    type: str = Field(description="Message type: user, assistant, queue-operation, system, etc.")
    contents: List[MessageContent] = Field(description="List of content blocks")
    timestamp: datetime = Field(description="Message timestamp")
    parent_uuid: Optional[str] = Field(None, description="Parent message UUID")
    model: Optional[str] = Field(None, description="Model used for this message")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage info")
    error: Optional[str] = Field(None, description="Error message if any")

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
