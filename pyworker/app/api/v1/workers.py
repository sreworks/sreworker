"""Worker REST API routes - V1."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends

from ...models.worker import WorkerResponse, CreateWorkerRequest
from ...db import DatabaseConnection, WorkerRepository
from ...db.database_models import WorkerDO
from ...workers import handlers, default as default_type

router = APIRouter(prefix="/api/v1/workers", tags=["Workers"])

# Database connection (set by main.py)
db_conn: DatabaseConnection = None


def get_worker_repo() -> WorkerRepository:
    """Dependency to get worker repository."""
    if db_conn is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return WorkerRepository(db_conn.conn)


@router.get("", response_model=dict)
async def list_workers(repo: WorkerRepository = Depends(get_worker_repo)):
    """List all workers."""
    workers = repo.list_all()

    return {
        "workers": [
            WorkerResponse(
                name=w.id,
                type=w.type,
                env_vars=w.env_vars,
                command_params=w.command_params,
                created_at=w.created_at
            )
            for w in workers
        ]
    }


@router.post("", response_model=WorkerResponse, status_code=201)
async def create_worker(
    request: CreateWorkerRequest,
    repo: WorkerRepository = Depends(get_worker_repo)
):
    """Create a new worker."""
    existing = repo.get(request.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Worker '{request.name}' already exists")

    # Validate worker type
    if request.type not in handlers:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown worker type: '{request.type}'. Available types: {list(handlers.keys())}"
        )

    worker = WorkerDO(
        id=request.name,
        type=request.type,
        env_vars=request.env_vars or {},
        command_params=request.command_params or [],
        created_at=datetime.utcnow()
    )

    if not repo.create(worker):
        raise HTTPException(status_code=500, detail="Failed to create worker")

    return WorkerResponse(
        name=worker.id,
        type=worker.type,
        env_vars=worker.env_vars,
        command_params=worker.command_params,
        created_at=worker.created_at
    )


@router.get("/types", response_model=dict)
async def list_worker_types():
    """List available worker types."""
    return {
        "types": list(handlers.keys()),
        "default": default_type
    }


@router.get("/{worker_name}", response_model=WorkerResponse)
async def get_worker(
    worker_name: str,
    repo: WorkerRepository = Depends(get_worker_repo)
):
    """Get worker details."""
    worker = repo.get(worker_name)

    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker not found: {worker_name}")

    return WorkerResponse(
        name=worker.id,
        type=worker.type,
        env_vars=worker.env_vars,
        command_params=worker.command_params,
        created_at=worker.created_at
    )


@router.delete("/{worker_name}", response_model=dict)
async def delete_worker(
    worker_name: str,
    repo: WorkerRepository = Depends(get_worker_repo)
):
    """Delete a worker."""
    worker = repo.get(worker_name)

    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker not found: {worker_name}")

    if not repo.delete(worker_name):
        raise HTTPException(status_code=500, detail="Failed to delete worker")

    return {
        "status": "deleted",
        "message": f"Worker {worker_name} deleted successfully"
    }
