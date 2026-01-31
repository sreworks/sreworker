"""AI CLI configuration model."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class AICLIConfig(BaseModel):
    """AI CLI configuration model."""

    type: str = Field(..., description="AI CLI type identifier (e.g., 'claude', 'opencode')")
    name: str = Field(..., description="Human-readable name")
    binary: str = Field(..., description="Binary/executable path")
    version: Optional[str] = Field(default=None, description="Version information")
    enabled: bool = Field(default=True, description="Whether this CLI is enabled")
    description: Optional[str] = Field(default=None, description="Description of this AI CLI")
    config_options: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration options")


class AICLIListResponse(BaseModel):
    """Response model for listing available AI CLIs."""

    available_clis: list[AICLIConfig] = Field(..., description="List of available AI CLIs")
    default: str = Field(..., description="Default AI CLI type")
