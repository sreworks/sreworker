"""Worker 抽象基类"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from ...models.message import MessageResponse

if TYPE_CHECKING:
    from ...services.file_manager import FileManager


class BaseWorker(ABC):
    """Worker 业务逻辑抽象接口"""

    def __init__(self, env_vars: Optional[Dict[str, str]], command_params: Optional[List[str]],
                 file_manager: Optional["FileManager"] = None):
        self.file_manager = file_manager

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
    async def fetch_messages(self, raw_conversation_id: str) -> List[MessageResponse]:
        """
        从代码工具侧读取并转换会话消息

        Args:
            raw_conversation_id: 代码工具侧的会话 ID

        Returns:
            标准化消息列表
        """
        pass



