"""Worker API models."""

import re
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator


# Worker name pattern: alphanumeric, hyphens, underscores, 1-64 chars
WORKER_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,63}$')


class CreateWorkerRequest(BaseModel):
    """Request model for creating a worker."""

    name: str = Field(description="Worker name (used as ID)")
    type: str = Field(default="claudecode", description="Worker type")
    env_vars: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")
    command_params: Optional[List[str]] = Field(default_factory=list, description="Command line parameters")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate worker name format."""
        if not WORKER_NAME_PATTERN.match(v):
            raise ValueError(
                f"Invalid name '{v}'. Must start with a letter, "
                "contain only alphanumeric characters, hyphens, or underscores, "
                "and be 1-64 characters long."
            )
        return v


class WorkerResponse(BaseModel):
    """Response model for worker information."""

    name: str
    type: str
    env_vars: Dict[str, str]
    command_params: List[str]
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
