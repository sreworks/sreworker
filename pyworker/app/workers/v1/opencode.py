"""OpenCode Worker 实现"""

from typing import Optional, Dict, List, Any

from .base import BaseWorker


class OpenCodeWorker(BaseWorker):
    """OpenCode CLI Worker 实现 (TODO)"""

    def __init__(self, env_vars: Optional[Dict[str, str]] = None, command_params: Optional[List[str]] = None):
        self.env_vars = env_vars or {}
        self.command_params = command_params or []

    async def start_conversation(self, path: str, message: str) -> str:
        """启动新会话"""
        raise NotImplementedError("OpenCodeWorker not implemented yet")

    async def achieve_conversation(self, raw_conversation_id: str) -> bool:
        """归档会话"""
        raise NotImplementedError("OpenCodeWorker not implemented yet")

    async def continue_conversation(self, raw_conversation_id: str, path: str, message: str) -> bool:
        """继续已有会话"""
        raise NotImplementedError("OpenCodeWorker not implemented yet")

    async def sync_messages(self, raw_conversation_id: str) -> List[Dict[str, Any]]:
        """从 OpenCode 同步会话消息"""
        raise NotImplementedError("OpenCodeWorker not implemented yet")
