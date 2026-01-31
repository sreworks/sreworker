"""Worker 抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ...services.v1.conversation_manager import BaseConversationManager


class BaseWorker(ABC):
    """Worker 业务逻辑抽象接口"""

    def __init__(self, worker_id: str, config: Dict[str, Any]):
        """
        初始化 Worker

        Args:
            worker_id: Worker 唯一标识符
            config: Worker 配置
        """
        self.worker_id = worker_id
        self.config = config
        self._conversation_manager: Optional[BaseConversationManager] = None

    # === 生命周期管理 ===
    @abstractmethod
    async def start(self) -> bool:
        """
        启动 worker

        Returns:
            True if started successfully, False otherwise
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止 worker"""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """
        检查 worker 是否正在运行

        Returns:
            True if running, False otherwise
        """
        pass

    # === 消息管理 ===
    @abstractmethod
    async def send_message(self, message: str, conversation_id: Optional[str] = None) -> bool:
        """
        发送消息

        Args:
            message: 要发送的消息
            conversation_id: 可选的对话 ID，如果不提供则发送到当前对话

        Returns:
            True if message was sent successfully, False otherwise
        """
        pass

    # === 状态获取 ===
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """
        获取 worker 状态

        Returns:
            状态信息字典
        """
        pass

    # === Conversation Manager 访问 ===
    def get_conversation_manager(self) -> BaseConversationManager:
        """
        获取对话管理器

        Returns:
            对话管理器实例

        Raises:
            RuntimeError: 如果对话管理器未初始化
        """
        if self._conversation_manager is None:
            raise RuntimeError("Conversation manager not initialized")
        return self._conversation_manager

    @abstractmethod
    def _create_conversation_manager(self) -> BaseConversationManager:
        """
        创建对话管理器（由子类实现）

        Returns:
            对话管理器实例
        """
        pass

    # === 工具方法 ===
    def get_worker_type(self) -> str:
        """
        获取 worker 类型

        Returns:
            Worker 类型名称
        """
        return self.__class__.__name__.replace("Worker", "").lower()
