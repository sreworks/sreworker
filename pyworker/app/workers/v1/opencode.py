"""OpenCode Worker 实现"""

from typing import TYPE_CHECKING, Optional, Dict, List, Any

from .base import BaseWorker
from ...models.message import MessageResponse

if TYPE_CHECKING:
    from ...services.file_manager import FileManager


class OpenCodeWorker(BaseWorker):
    """OpenCode CLI Worker 实现 (TODO)"""

    def __init__(self, env_vars: Optional[Dict[str, str]] = None,
                 command_params: Optional[List[str]] = None,
                 file_manager: Optional["FileManager"] = None):
        super().__init__(env_vars, command_params, file_manager)
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

    async def fetch_messages(self, raw_conversation_id: str) -> List[MessageResponse]:
        """从 OpenCode 读取并转换会话消息"""
        raise NotImplementedError("OpenCodeWorker not implemented yet")
