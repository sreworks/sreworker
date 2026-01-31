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
    type: str = Field(default="claudecode", description="AI CLI type (claudecode, opencode, etc.)")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    command_params: List[str] = Field(default_factory=list, description="Command line parameters")
    status: WorkerStatus = Field(default=WorkerStatus.CREATED, description="Worker status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    last_activity: Optional[datetime] = Field(default=None, description="Last activity timestamp")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateWorkerRequest(BaseModel):
    """Request model for creating a worker."""

    type: str = Field(default="claudecode", description="AI CLI type (claudecode, opencode, etc.)")
    env_vars: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")
    command_params: Optional[List[str]] = Field(default_factory=list, description="Command line parameters")


class WorkerResponse(BaseModel):
    """Response model for worker information."""

    id: str
    type: str
    env_vars: Dict[str, str]
    command_params: List[str]
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

    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Recent messages")
