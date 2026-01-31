"""Conversation database model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class ConversationDO:
    """Conversation data object - maps to conversations table."""

    id: str
    worker_id: str
    project_path: str
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_current: bool = False
    raw_conversation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
