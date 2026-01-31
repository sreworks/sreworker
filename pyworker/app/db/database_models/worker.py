"""Worker database model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class WorkerDO:
    """Worker data object - maps to workers table."""

    id: str
    type: str
    env_vars: Dict[str, str] = field(default_factory=dict)
    command_params: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
