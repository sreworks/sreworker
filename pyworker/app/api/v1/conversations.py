"""Conversation REST API routes - V1."""

import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query

from ...models.conversation import (
    ConversationResponse,
    ConversationListResponse,
    CreateConversationRequest,
    RenameConversationRequest,
    CreateMessageRequest,
    ConversationMessageResponse,
    MessageResponse
)
from ...db import DatabaseConnection, ConversationRepository, WorkerRepository
from ...db.database_models import ConversationDO
from ...services import ConversationManager

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])

# Database connection (set by main.py)
db_conn: DatabaseConnection = None
# Conversation manager for file-based message storage (set by main.py)
conv_manager: ConversationManager = None


def get_conversation_repo() -> ConversationRepository:
    """Dependency to get conversation repository."""
    if db_conn is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return ConversationRepository(db_conn.conn)


def get_conv_manager() -> ConversationManager:
    """Dependency to get conversation manager."""
    if conv_manager is None:
        raise HTTPException(status_code=500, detail="Conversation manager not initialized")
    return conv_manager


def get_worker_repo() -> WorkerRepository:
    """Dependency to get worker repository."""
    if db_conn is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return WorkerRepository(db_conn.conn)


def _to_response(conv: ConversationDO) -> ConversationResponse:
    """Convert ConversationDO to ConversationResponse."""
    return ConversationResponse(
        id=conv.id,
        worker_name=conv.worker_id,
        name=conv.name,
        project_path=conv.project_path,
        created_at=conv.created_at,
        last_activity=conv.last_activity,
        is_current=conv.is_current,
        raw_conversation_id=conv.raw_conversation_id,
        metadata=conv.metadata
    )


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    worker_name: Optional[str] = Query(None, description="Filter by worker name"),
    repo: ConversationRepository = Depends(get_conversation_repo)
):
    """List all conversations, optionally filtered by worker_name."""
    if worker_name:
        conversations = repo.list_by_worker(worker_name)
    else:
        conversations = repo.list_all()

    return ConversationListResponse(
        conversations=[_to_response(c) for c in conversations],
        total=len(conversations)
    )


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: CreateConversationRequest,
    conv_repo: ConversationRepository = Depends(get_conversation_repo),
    worker_repo: WorkerRepository = Depends(get_worker_repo)
):
    """Create a new conversation."""
    worker = worker_repo.get(request.worker_name)
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker not found: {request.worker_name}")

    now = datetime.utcnow()
    conversation = ConversationDO(
        id=str(uuid.uuid4()),
        worker_id=request.worker_name,
        project_path=request.project_path,
        name=request.name or f"Conversation {now.strftime('%Y-%m-%d %H:%M')}",
        created_at=now,
        last_activity=now,
        is_current=True,
        raw_conversation_id=None,
        metadata={}
    )

    if not conv_repo.create(conversation):
        raise HTTPException(status_code=500, detail="Failed to create conversation")

    return _to_response(conversation)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    repo: ConversationRepository = Depends(get_conversation_repo)
):
    """Get conversation details."""
    conversation = repo.get(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")

    return _to_response(conversation)


@router.delete("/{conversation_id}", response_model=dict)
async def delete_conversation(
    conversation_id: str,
    conv_repo: ConversationRepository = Depends(get_conversation_repo),
    manager: ConversationManager = Depends(get_conv_manager)
):
    """Delete a conversation and its messages."""
    conversation = conv_repo.get(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")

    # Delete message file
    manager.delete_conversation(conversation.worker_id, conversation_id)

    if not conv_repo.delete(conversation_id):
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

    return {
        "status": "deleted",
        "message": f"Conversation {conversation_id} deleted successfully"
    }


@router.patch("/{conversation_id}", response_model=dict)
async def rename_conversation(
    conversation_id: str,
    request: RenameConversationRequest,
    repo: ConversationRepository = Depends(get_conversation_repo)
):
    """Rename a conversation."""
    conversation = repo.get(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")

    if not repo.update(conversation_id, {"name": request.new_name}):
        raise HTTPException(status_code=500, detail="Failed to rename conversation")

    return {
        "status": "success",
        "message": f"Conversation renamed to '{request.new_name}'"
    }


@router.get("/{conversation_id}/messages", response_model=ConversationMessageResponse)
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=1000),
    conv_repo: ConversationRepository = Depends(get_conversation_repo),
    manager: ConversationManager = Depends(get_conv_manager)
):
    """Get messages from a conversation."""
    conversation = conv_repo.get(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")

    messages = manager.get_messages(conversation.worker_id, conversation_id, limit=limit)

    return ConversationMessageResponse(
        conversation_id=conversation_id,
        messages=[
            MessageResponse(
                id=None,
                conversation_id=conversation_id,
                worker_name=conversation.worker_id,
                role=m["role"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
                metadata=m.get("metadata", {})
            )
            for m in messages
        ],
        total=len(messages)
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def create_message(
    conversation_id: str,
    request: CreateMessageRequest,
    conv_repo: ConversationRepository = Depends(get_conversation_repo),
    manager: ConversationManager = Depends(get_conv_manager)
):
    """Add a message to a conversation."""
    conversation = conv_repo.get(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")

    message = manager.add_message(
        worker_name=conversation.worker_id,
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        metadata=request.metadata
    )

    # Update last_activity
    conv_repo.update(conversation_id, {"last_activity": datetime.utcnow()})

    return MessageResponse(
        id=None,
        conversation_id=conversation_id,
        worker_name=conversation.worker_id,
        role=message["role"],
        content=message["content"],
        timestamp=datetime.fromisoformat(message["timestamp"]),
        metadata=message.get("metadata", {})
    )
