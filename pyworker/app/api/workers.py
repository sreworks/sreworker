"""Worker REST API routes."""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from ..models.worker import (
    WorkerResponse,
    WorkerDetailResponse,
    CreateWorkerRequest,
    WorkerStatus
)
from ..models.ai_cli import AICLIListResponse
from ..services.worker_manager import WorkerManager
from ..adapters.registry import adapter_registry
from ..config import settings

router = APIRouter(prefix="/api", tags=["workers"])

# Global worker manager instance (will be set by main.py)
worker_manager: WorkerManager = None


def get_worker_manager() -> WorkerManager:
    """Dependency to get worker manager instance."""
    if worker_manager is None:
        raise HTTPException(status_code=500, detail="Worker manager not initialized")
    return worker_manager


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
        "total_workers": len(workers),
        "max_workers": settings.max_workers,
        "enabled_ai_clis": settings.get_enabled_ai_clis()
    }
