"""Worker 抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class BaseWorker(ABC):
    """Worker 业务逻辑抽象接口"""

    def __init__(self, env_vars: Optional[Dict[str, str]], command_params: Optional[List[str]]):
        pass

    @abstractmethod
    async def start_conversation(self, path, message) -> str:
        """
        启动 会话

        Returns:
            raw_conversation_id
        """
        pass

    @abstractmethod
    async def achieve_conversation(self, raw_conversation_id) -> bool:
        """
        归档 会话

        """
        pass

    @abstractmethod
    async def continue_conversation(self, raw_conversation_id: str, path: str, message: str) -> bool:
        """
        继续 会话

        Args:
            raw_conversation_id: 代码工具侧的会话 ID
            path: 工作目录路径
            message: 消息内容

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def sync_messages(self, raw_conversation_id: str) -> List[Dict[str, Any]]:
        """
        从代码工具侧同步会话消息

        Args:
            raw_conversation_id: 代码工具侧的会话 ID

        Returns:
            原始消息列表（代码工具的原始 JSON 格式）
        """
        pass



