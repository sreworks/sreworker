"""Worker data model."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid


class WorkerStatus(str, Enum):
    """Worker status enum."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class WorkerModel(BaseModel):
    """Worker data model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Worker unique ID")
    name: str = Field(..., description="Worker name")
    ai_cli_type: str = Field(default="claude", description="AI CLI type (claude, opencode, etc.)")
    status: WorkerStatus = Field(default=WorkerStatus.CREATED, description="Worker status")
    config: Dict[str, Any] = Field(default_factory=dict, description="Worker configuration")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    last_activity: Optional[datetime] = Field(default=None, description="Last activity timestamp")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateWorkerRequest(BaseModel):
    """Request model for creating a worker."""

    name: str = Field(..., description="Worker name", min_length=1, max_length=100)
    ai_cli_type: Optional[str] = Field(default="claude", description="AI CLI type")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Worker configuration")


class WorkerResponse(BaseModel):
    """Response model for worker information."""

    id: str
    name: str
    ai_cli_type: str
    status: WorkerStatus
    created_at: datetime
    last_activity: Optional[datetime]

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkerDetailResponse(WorkerResponse):
    """Detailed response model for worker information."""

    config: Dict[str, Any]
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Recent messages")
