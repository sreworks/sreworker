"""Worker REST API routes - V1"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from ...models.v1.worker import (
    WorkerResponse,
    WorkerDetailResponse,
    CreateWorkerRequest,
    WorkerStatus
)
from ...models.v1.conversation import (
    ConversationResponse,
    ConversationListResponse,
    CreateConversationRequest,
    CloneConversationRequest,
    RenameConversationRequest,
    ConversationMessageResponse
)
from ...models.v1.ai_cli import AICLIListResponse
from ...services.v1.worker_manager import WorkerManager
from ...adapters.v1.registry import adapter_registry
from ...config import settings

router = APIRouter(prefix="/api/v1", tags=["workers-v1"])

# Global worker manager instance (will be set by main.py)
worker_manager: WorkerManager = None


def get_worker_manager() -> WorkerManager:
    """Dependency to get worker manager instance."""
    if worker_manager is None:
        raise HTTPException(status_code=500, detail="Worker manager not initialized")
    return worker_manager


# === Worker Management Endpoints ===

@router.get("/workers", response_model=dict)
async def list_workers(manager: WorkerManager = Depends(get_worker_manager)):
    """
    List all workers.

    Returns:
        Dictionary containing list of workers
    """
    workers = manager.list_workers()

    worker_responses = [
        WorkerResponse(
            id=worker.id,
            name=worker.name,
            project_path=worker.project_path,
            ai_cli_type=worker.ai_cli_type,
            status=worker.status,
            created_at=worker.created_at,
            last_activity=worker.last_activity
        )
        for worker in workers
    ]

    return {"workers": worker_responses}


@router.post("/workers", response_model=WorkerResponse, status_code=201)
async def create_worker(
    request: CreateWorkerRequest,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Create a new worker.

    Args:
        request: Worker creation request

    Returns:
        Created worker information

    Raises:
        HTTPException: If worker creation fails
    """
    try:
        worker = await manager.create_worker(request)

        return WorkerResponse(
            id=worker.id,
            name=worker.name,
            project_path=worker.project_path,
            ai_cli_type=worker.ai_cli_type,
            status=worker.status,
            created_at=worker.created_at,
            last_activity=worker.last_activity
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create worker: {str(e)}")


@router.get("/workers/{worker_id}", response_model=WorkerDetailResponse)
async def get_worker(
    worker_id: str,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Get worker details.

    Args:
        worker_id: Worker ID

    Returns:
        Worker details including message history

    Raises:
        HTTPException: If worker not found
    """
    worker = manager.get_worker(worker_id)

    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker not found: {worker_id}")

    # Get recent messages
    messages = manager.get_message_history(worker_id, limit=50)

    return WorkerDetailResponse(
        id=worker.id,
        name=worker.name,
        project_path=worker.project_path,
        ai_cli_type=worker.ai_cli_type,
        status=worker.status,
        created_at=worker.created_at,
        last_activity=worker.last_activity,
        config=worker.config,
        messages=messages
    )


@router.delete("/workers/{worker_id}", response_model=dict)
async def delete_worker(
    worker_id: str,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Delete a worker.

    Args:
        worker_id: Worker ID

    Returns:
        Success message

    Raises:
        HTTPException: If worker not found or deletion fails
    """
    try:
        await manager.delete_worker(worker_id)
        return {
            "status": "deleted",
            "message": f"Worker {worker_id} deleted successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete worker: {str(e)}")


# === Conversation Management Endpoints ===

@router.get("/workers/{worker_id}/conversations", response_model=ConversationListResponse)
async def list_conversations(
    worker_id: str,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    List all conversations for a worker.

    Args:
        worker_id: Worker ID

    Returns:
        List of conversations

    Raises:
        HTTPException: If worker not found
    """
    try:
        conversations_data = await manager.list_conversations(worker_id)

        conversations = [
            ConversationResponse(**conv)
            for conv in conversations_data
        ]

        return ConversationListResponse(
            conversations=conversations,
            total=len(conversations)
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@router.post("/workers/{worker_id}/conversations", response_model=dict, status_code=201)
async def create_conversation(
    worker_id: str,
    request: Optional[CreateConversationRequest] = None,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Create a new conversation for a worker.

    Args:
        worker_id: Worker ID
        request: Optional conversation creation request

    Returns:
        Conversation ID

    Raises:
        HTTPException: If worker not found or creation fails
    """
    try:
        name = request.name if request else None
        conversation_id = await manager.new_conversation(worker_id, name)

        return {
            "conversation_id": conversation_id,
            "message": "Conversation created successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


@router.get("/workers/{worker_id}/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    worker_id: str,
    conversation_id: str,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Get conversation details.

    Args:
        worker_id: Worker ID
        conversation_id: Conversation ID

    Returns:
        Conversation details

    Raises:
        HTTPException: If worker or conversation not found
    """
    try:
        conversation_data = await manager.get_conversation(worker_id, conversation_id)

        if not conversation_data:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation not found: {conversation_id}"
            )

        return ConversationResponse(**conversation_data)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@router.post("/workers/{worker_id}/conversations/{conversation_id}/clone", response_model=dict, status_code=201)
async def clone_conversation(
    worker_id: str,
    conversation_id: str,
    request: Optional[CloneConversationRequest] = None,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Clone a conversation.

    Args:
        worker_id: Worker ID
        conversation_id: Conversation ID to clone
        request: Optional clone request with new name

    Returns:
        New conversation ID

    Raises:
        HTTPException: If worker or conversation not found
    """
    try:
        new_name = request.new_name if request else None
        new_id = await manager.clone_conversation(worker_id, conversation_id, new_name)

        return {
            "conversation_id": new_id,
            "message": "Conversation cloned successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clone conversation: {str(e)}")


@router.delete("/workers/{worker_id}/conversations/{conversation_id}", response_model=dict)
async def delete_conversation(
    worker_id: str,
    conversation_id: str,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Delete a conversation.

    Args:
        worker_id: Worker ID
        conversation_id: Conversation ID

    Returns:
        Success message

    Raises:
        HTTPException: If worker or conversation not found
    """
    try:
        success = await manager.delete_conversation(worker_id, conversation_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation not found: {conversation_id}"
            )

        return {
            "status": "deleted",
            "message": f"Conversation {conversation_id} deleted successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")


@router.post("/workers/{worker_id}/conversations/{conversation_id}/switch", response_model=dict)
async def switch_conversation(
    worker_id: str,
    conversation_id: str,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Switch to a conversation.

    Args:
        worker_id: Worker ID
        conversation_id: Conversation ID

    Returns:
        Success message

    Raises:
        HTTPException: If worker or conversation not found
    """
    try:
        success = await manager.switch_conversation(worker_id, conversation_id)

        return {
            "status": "success",
            "message": f"Switched to conversation {conversation_id}",
            "current_conversation": conversation_id
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch conversation: {str(e)}")


@router.patch("/workers/{worker_id}/conversations/{conversation_id}", response_model=dict)
async def rename_conversation(
    worker_id: str,
    conversation_id: str,
    request: RenameConversationRequest,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Rename a conversation.

    Args:
        worker_id: Worker ID
        conversation_id: Conversation ID
        request: Rename request with new name

    Returns:
        Success message

    Raises:
        HTTPException: If worker or conversation not found
    """
    try:
        success = await manager.rename_conversation(worker_id, conversation_id, request.new_name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation not found: {conversation_id}"
            )

        return {
            "status": "success",
            "message": f"Conversation renamed to '{request.new_name}'"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename conversation: {str(e)}")


@router.get("/workers/{worker_id}/conversations/{conversation_id}/messages", response_model=ConversationMessageResponse)
async def get_conversation_messages(
    worker_id: str,
    conversation_id: str,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Get messages from a conversation.

    Args:
        worker_id: Worker ID
        conversation_id: Conversation ID

    Returns:
        Conversation messages

    Raises:
        HTTPException: If worker or conversation not found
    """
    try:
        messages = await manager.get_conversation_messages(worker_id, conversation_id)

        return ConversationMessageResponse(
            conversation_id=conversation_id,
            messages=messages,
            total=len(messages)
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation messages: {str(e)}")


@router.get("/workers/{worker_id}/conversations/current", response_model=dict)
async def get_current_conversation(
    worker_id: str,
    manager: WorkerManager = Depends(get_worker_manager)
):
    """
    Get current active conversation for a worker.

    Args:
        worker_id: Worker ID

    Returns:
        Current conversation ID

    Raises:
        HTTPException: If worker not found
    """
    try:
        current_id = manager.get_current_conversation(worker_id)

        return {
            "worker_id": worker_id,
            "current_conversation": current_id
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current conversation: {str(e)}")


# === Other Endpoints ===

@router.get("/ai-clis", response_model=AICLIListResponse)
async def list_ai_clis():
    """
    List available AI CLIs.

    Returns:
        List of available AI CLI configurations
    """
    available_clis = adapter_registry.list_available_adapters()

    return AICLIListResponse(
        available_clis=available_clis,
        default=settings.default_ai_cli
    )


@router.get("/health", response_model=dict)
async def health_check(manager: WorkerManager = Depends(get_worker_manager)):
    """
    Health check endpoint.

    Returns:
        Health status information
    """
    workers = manager.list_workers()

    return {
        "status": "healthy",
        "version": "v1",
        "total_workers": len(workers),
        "max_workers": settings.max_workers,
        "enabled_ai_clis": settings.get_enabled_ai_clis()
    }
