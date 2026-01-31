"""Conversation data models - V1"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ConversationResponse(BaseModel):
    """Response model for conversation information"""

    id: str = Field(..., description="Conversation ID")
    name: str = Field(..., description="Conversation name")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    last_activity: str = Field(..., description="Last activity timestamp (ISO format)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "My Conversation",
                "created_at": "2024-01-30T12:00:00",
                "last_activity": "2024-01-30T13:30:00",
                "metadata": {}
            }
        }


class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation"""

    name: Optional[str] = Field(None, description="Conversation name", max_length=200)

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "name": "New Conversation"
            }
        }


class CloneConversationRequest(BaseModel):
    """Request model for cloning a conversation"""

    new_name: Optional[str] = Field(None, description="Name for the cloned conversation", max_length=200)

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "new_name": "Cloned Conversation"
            }
        }


class RenameConversationRequest(BaseModel):
    """Request model for renaming a conversation"""

    new_name: str = Field(..., description="New conversation name", min_length=1, max_length=200)

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "new_name": "Updated Conversation Name"
            }
        }


class ConversationListResponse(BaseModel):
    """Response model for listing conversations"""

    conversations: List[ConversationResponse] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "conversations": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "My Conversation",
                        "created_at": "2024-01-30T12:00:00",
                        "last_activity": "2024-01-30T13:30:00",
                        "metadata": {}
                    }
                ],
                "total": 1
            }
        }


class ConversationMessageResponse(BaseModel):
    """Response model for conversation messages"""

    messages: List[Dict[str, Any]] = Field(..., description="List of messages")
    conversation_id: str = Field(..., description="Conversation ID")
    total: int = Field(..., description="Total number of messages")

    class Config:
        """Pydantic configuration"""
        schema_extra = {
            "example": {
                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                "messages": [
                    {
                        "type": "user",
                        "content": "Hello",
                        "timestamp": "2024-01-30T12:00:00"
                    },
                    {
                        "type": "assistant",
                        "content": "Hi! How can I help you?",
                        "timestamp": "2024-01-30T12:00:05"
                    }
                ],
                "total": 2
            }
        }
