"""Worker data model."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
import uuid

from ...workers.v1 import handlers, default as default_type


class WorkerModel(BaseModel):
    """Worker data model - a storage record for worker configuration."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Worker unique ID")
    type: str = Field(default_factory=lambda: default_type, description="AI CLI type")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    command_params: List[str] = Field(default_factory=list, description="Command line parameters")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateWorkerRequest(BaseModel):
    """Request model for creating a worker."""

    type: str = Field(default_factory=lambda: default_type, description="AI CLI type")
    env_vars: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")
    command_params: Optional[List[str]] = Field(default_factory=list, description="Command line parameters")

    @validator('type')
    def validate_type(cls, v):
        v = v.lower()
        if v not in handlers:
            raise ValueError(f"Unknown type '{v}'. Available: {list(handlers.keys())}")
        return v


class WorkerResponse(BaseModel):
    """Response model for worker information."""

    id: str
    type: str
    env_vars: Dict[str, str]
    command_params: List[str]
    created_at: datetime

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
