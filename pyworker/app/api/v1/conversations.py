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
    CreateInputRequest,
    ConversationInputResponse,
    InputResponse
)
from ...models.message import (
    MessageResponse,
    ConversationMessagesResponse,
    SyncMessagesResponse
)
from ...db import DatabaseConnection, ConversationRepository, WorkerRepository
from ...db.database_models import ConversationDO
from ...services import ConversationManager
from ...services.file_manager import FileManager
from ...workers import handlers

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])

# Database connection (set by main.py)
db_conn: DatabaseConnection = None
# Conversation manager for file-based message storage (set by main.py)
conv_manager: ConversationManager = None
# File manager for file monitoring (set by main.py)
file_manager: FileManager = None


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
    from pathlib import Path

    # 检查 project_path 是否存在且为目录
    p = Path(request.project_path)
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"project_path does not exist: {request.project_path}")
    if not p.is_dir():
        raise HTTPException(status_code=400, detail=f"project_path is not a directory: {request.project_path}")

    worker = worker_repo.get(request.worker_name)
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker not found: {request.worker_name}")

    now = datetime.utcnow()
    conversation = ConversationDO(
        id=str(uuid.uuid4()),
        worker_id=request.worker_name,
        project_path=request.project_path,
        name=request.name,
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


@router.get("/{conversation_id}/inputs", response_model=ConversationInputResponse)
async def get_conversation_inputs(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=1000),
    conv_repo: ConversationRepository = Depends(get_conversation_repo),
    manager: ConversationManager = Depends(get_conv_manager)
):
    """Get inputs from a conversation."""
    conversation = conv_repo.get(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")

    inputs = manager.get_inputs(conversation.worker_id, conversation_id, limit=limit)

    return ConversationInputResponse(
        conversation_id=conversation_id,
        inputs=[
            InputResponse(
                id=None,
                conversation_id=conversation_id,
                worker_name=conversation.worker_id,
                role=m["role"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
                metadata=m.get("metadata", {})
            )
            for m in inputs
        ],
        total=len(inputs)
    )


@router.post("/{conversation_id}", response_model=InputResponse, status_code=201)
async def create_input(
    conversation_id: str,
    request: CreateInputRequest,
    conv_repo: ConversationRepository = Depends(get_conversation_repo),
    worker_repo: WorkerRepository = Depends(get_worker_repo),
    manager: ConversationManager = Depends(get_conv_manager)
):
    """Add an input to a conversation."""
    conversation = conv_repo.get(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")

    # Get worker record
    worker_record = worker_repo.get(conversation.worker_id)
    if not worker_record:
        raise HTTPException(status_code=404, detail=f"Worker not found: {conversation.worker_id}")

    # Get worker class from handlers registry
    worker_class = handlers.get(worker_record.type)
    if not worker_class:
        raise HTTPException(status_code=400, detail=f"Unknown worker type: {worker_record.type}")

    # Instantiate worker
    worker_instance = worker_class(
        env_vars=worker_record.env_vars,
        command_params=worker_record.command_params,
        file_manager=file_manager
    )

    # Call worker based on whether we have a raw_conversation_id
    if conversation.raw_conversation_id is None:
        # First input - start new conversation
        try:
            raw_conversation_id = await worker_instance.start_conversation(
                path=conversation.project_path,
                message=request.content
            )
            # Save raw_conversation_id back to conversation
            conv_repo.update(conversation_id, {"raw_conversation_id": raw_conversation_id})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start conversation: {str(e)}")
    else:
        # Continue existing conversation
        # 先注册 session 监控，再发消息，这样 watch 不会错过文件变更
        if hasattr(worker_class, 'activate_session'):
            worker_class.activate_session(
                conversation.raw_conversation_id, conversation_id, conversation.worker_id
            )
        if hasattr(worker_class, '_conv_manager_ref') and worker_class._conv_manager_ref is None:
            worker_class._conv_manager_ref = conv_manager
        try:
            await worker_instance.continue_conversation(
                raw_conversation_id=conversation.raw_conversation_id,
                path=conversation.project_path,
                message=request.content
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to continue conversation: {str(e)}")

    # 激活 session 监控 — start 场景在这里注册（continue 场景已在上面提前注册，这里幂等覆盖）
    actual_raw_id = (raw_conversation_id
                     if conversation.raw_conversation_id is None
                     else conversation.raw_conversation_id)
    if hasattr(worker_class, 'activate_session'):
        worker_class.activate_session(actual_raw_id, conversation_id, conversation.worker_id)
    # 注入 conv_manager 引用，供 watch 回调自动保存
    if hasattr(worker_class, '_conv_manager_ref') and worker_class._conv_manager_ref is None:
        worker_class._conv_manager_ref = conv_manager

    # 立即执行一次 sync，防止 watch 激活晚于初始写入
    try:
        messages = await worker_instance.sync_messages(actual_raw_id)
        if messages:
            manager.save_messages(conversation.worker_id, conversation_id, messages)
    except Exception:
        pass  # 非致命，后续 watch 或 polling 会补上

    # Save input to local storage
    input_data = manager.add_input(
        worker_name=conversation.worker_id,
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        metadata=request.metadata
    )

    # Update last_activity
    conv_repo.update(conversation_id, {"last_activity": datetime.utcnow()})

    return InputResponse(
        id=None,
        conversation_id=conversation_id,
        worker_name=conversation.worker_id,
        role=input_data["role"],
        content=input_data["content"],
        timestamp=datetime.fromisoformat(input_data["timestamp"]),
        metadata=input_data.get("metadata", {})
    )


@router.get("/{conversation_id}/messages", response_model=ConversationMessagesResponse)
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

    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=messages,
        total=len(messages)
    )


@router.post("/{conversation_id}/messages/sync", response_model=SyncMessagesResponse)
async def sync_conversation_messages(
    conversation_id: str,
    conv_repo: ConversationRepository = Depends(get_conversation_repo),
    worker_repo: WorkerRepository = Depends(get_worker_repo),
    manager: ConversationManager = Depends(get_conv_manager)
):
    """Sync messages from code tool for a conversation."""
    conversation = conv_repo.get(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {conversation_id}")

    if not conversation.raw_conversation_id:
        raise HTTPException(status_code=400, detail="Conversation has no raw_conversation_id, cannot sync")

    # Get worker record
    worker_record = worker_repo.get(conversation.worker_id)
    if not worker_record:
        raise HTTPException(status_code=404, detail=f"Worker not found: {conversation.worker_id}")

    # Get worker class from handlers registry
    worker_class = handlers.get(worker_record.type)
    if not worker_class:
        raise HTTPException(status_code=400, detail=f"Unknown worker type: {worker_record.type}")

    # Instantiate worker
    worker_instance = worker_class(
        env_vars=worker_record.env_vars,
        command_params=worker_record.command_params,
        file_manager=file_manager
    )

    # Sync messages from code tool (already standardized by worker)
    try:
        messages = await worker_instance.sync_messages(conversation.raw_conversation_id)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail=f"sync_messages not implemented for worker type: {worker_record.type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync messages: {str(e)}")

    # Save standardized messages to JSONL file (full overwrite)
    synced_count = manager.save_messages(conversation.worker_id, conversation_id, messages)

    return SyncMessagesResponse(
        conversation_id=conversation_id,
        synced_count=synced_count,
        total_messages=synced_count
    )
