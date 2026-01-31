"""Conversation API models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ConversationResponse(BaseModel):
    """Response model for conversation information."""

    id: str = Field(description="Conversation ID")
    worker_name: str = Field(description="Worker name this conversation belongs to")
    name: str = Field(description="Conversation name")
    project_path: str = Field(description="Project path for this conversation")
    created_at: datetime = Field(description="Creation timestamp")
    last_activity: datetime = Field(description="Last activity timestamp")
    is_current: bool = Field(default=False, description="Whether this is the current conversation")
    raw_conversation_id: Optional[str] = Field(None, description="Platform-specific conversation ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation."""

    worker_name: str = Field(description="Worker name to associate with this conversation")
    project_path: str = Field(description="Project path for this conversation", min_length=1)
    name: Optional[str] = Field(None, description="Conversation name", max_length=200)


class CloneConversationRequest(BaseModel):
    """Request model for cloning a conversation."""

    new_name: Optional[str] = Field(None, description="Name for the cloned conversation", max_length=200)


class RenameConversationRequest(BaseModel):
    """Request model for renaming a conversation."""

    new_name: str = Field(description="New conversation name", min_length=1, max_length=200)


class CreateMessageRequest(BaseModel):
    """Request model for creating a message."""

    role: str = Field(description="Message role (user/assistant)")
    content: str = Field(description="Message content", min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class ConversationListResponse(BaseModel):
    """Response model for listing conversations."""

    conversations: List[ConversationResponse] = Field(description="List of conversations")
    total: int = Field(description="Total number of conversations")


class MessageResponse(BaseModel):
    """Response model for a single message."""

    id: Optional[int] = Field(None, description="Message ID")
    conversation_id: str = Field(description="Conversation ID")
    worker_name: str = Field(description="Worker name")
    role: str = Field(description="Message role (user/assistant)")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationMessageResponse(BaseModel):
    """Response model for conversation messages."""

    conversation_id: str = Field(description="Conversation ID")
    messages: List[MessageResponse] = Field(description="List of messages")
    total: int = Field(description="Total number of messages")
