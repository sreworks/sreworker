"""OpenCode Worker 实现"""

from typing import Optional, Dict, Any, Callable
from .base import BaseWorker
from ...services.v1.conversation_manager import OpenCodeConversationManager, BaseConversationManager
from ...services.v1.process_handler import ProcessHandler
from ...adapters.v1.opencode import OpenCodeAdapter
from ...utils.logger import get_app_logger


class OpenCodeWorker(BaseWorker):
    """OpenCode 的业务逻辑实现"""

    def __init__(
        self,
        worker_id: str,
        project_path: str,
        config: Dict[str, Any],
        output_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        初始化 OpenCode Worker

        Args:
            worker_id: Worker ID
            project_path: 项目路径
            config: 配置信息
            output_callback: 输出回调函数
        """
        super().__init__(worker_id, project_path, config)

        # 初始化组件
        self.adapter = OpenCodeAdapter(config)
        self.process_handler: Optional[ProcessHandler] = None
        self.output_callback = output_callback
        self.logger = get_app_logger()

        # 初始化 conversation manager
        self._conversation_manager = self._create_conversation_manager()

    def _create_conversation_manager(self) -> BaseConversationManager:
        """创建 OpenCode 特定的对话管理器"""
        return OpenCodeConversationManager(
            project_path=self.project_path,
            worker_id=self.worker_id
        )

    async def start(self) -> bool:
        """启动 OpenCode worker"""
        try:
            # 创建输出回调
            def internal_output_callback(data: Dict[str, Any]):
                self._handle_output(data)

            # 创建并启动 ProcessHandler
            self.process_handler = ProcessHandler(
                worker_id=self.worker_id,
                project_path=self.project_path,
                adapter=self.adapter,
                output_callback=internal_output_callback
            )

            success = await self.process_handler.start()
            if not success:
                self.logger.error(f"Failed to start process handler for worker {self.worker_id}")
                return False

            # OpenCode 使用 stdout，不需要文件监视器

            self.logger.info(f"OpenCode worker {self.worker_id} started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start OpenCode worker {self.worker_id}: {e}")
            return False

    async def stop(self) -> None:
        """停止 worker"""
        try:
            # 停止进程处理器
            if self.process_handler:
                await self.process_handler.stop()
                self.process_handler = None
                self.logger.info(f"Process handler stopped for worker {self.worker_id}")

            self.logger.info(f"OpenCode worker {self.worker_id} stopped")

        except Exception as e:
            self.logger.error(f"Error stopping OpenCode worker {self.worker_id}: {e}")

    def is_running(self) -> bool:
        """检查 worker 是否正在运行"""
        if not self.process_handler:
            return False
        return self.process_handler.is_alive()

    async def send_message(self, message: str, conversation_id: Optional[str] = None) -> bool:
        """
        发送消息

        Args:
            message: 要发送的消息
            conversation_id: 可选的对话 ID，如果提供则先切换到该对话

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            # 如果指定了 conversation_id，先切换
            if conversation_id:
                current = self._conversation_manager.get_current_conversation()
                if current != conversation_id:
                    await self._conversation_manager.switch_conversation(conversation_id)
                    self.logger.info(f"Switched to conversation {conversation_id}")

            # 通过 ProcessHandler 发送消息
            if not self.process_handler:
                self.logger.error(f"Process handler not available for worker {self.worker_id}")
                return False

            success = await self.process_handler.send_message(message)

            if success:
                self.logger.debug(f"Message sent to worker {self.worker_id}: {message[:50]}...")
            else:
                self.logger.error(f"Failed to send message to worker {self.worker_id}")

            return success

        except Exception as e:
            self.logger.error(f"Error sending message to worker {self.worker_id}: {e}")
            return False

    async def get_status(self) -> Dict[str, Any]:
        """获取 worker 状态"""
        status = {
            "worker_id": self.worker_id,
            "type": "opencode",
            "project_path": self.project_path,
            "is_running": self.is_running(),
            "current_conversation": self._conversation_manager.get_current_conversation()
        }

        # 添加进程状态
        if self.process_handler:
            process_status = await self.process_handler.get_status()
            status.update({
                "process": process_status
            })

        return status

    def _handle_output(self, data: Dict[str, Any]):
        """
        处理输出数据

        Args:
            data: 输出数据
        """
        try:
            # 可以在这里做额外处理

            # 调用外部回调
            if self.output_callback:
                self.output_callback(data)

        except Exception as e:
            self.logger.error(f"Error handling output for worker {self.worker_id}: {e}")
