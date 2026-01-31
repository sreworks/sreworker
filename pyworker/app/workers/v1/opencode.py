"""OpenCode Worker 实现"""

from typing import Optional, Dict, Any, Callable, TYPE_CHECKING
from .base import BaseWorker
from ...services.v1.conversation_manager import OpenCodeConversationManager, BaseConversationManager
from ...services.v1.process_handler import ProcessHandler
from ...adapters.v1.opencode import OpenCodeAdapter
from ...utils.logger import get_app_logger

if TYPE_CHECKING:
    from ...services.v1.database import DatabaseManager


class OpenCodeWorker(BaseWorker):
    """OpenCode 的业务逻辑实现"""

    def __init__(
        self,
        worker_id: str,
        config: Dict[str, Any],
        output_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        db: Optional['DatabaseManager'] = None
    ):
        """
        初始化 OpenCode Worker

        Args:
            worker_id: Worker ID
            config: 配置信息
            output_callback: 输出回调函数
            db: 数据库管理器（可选）
        """
        super().__init__(worker_id, config)

        # 初始化组件
        self.adapter = OpenCodeAdapter(config)
        self.process_handler: Optional[ProcessHandler] = None
        self.output_callback = output_callback
        self.db = db
        self.logger = get_app_logger()

        # 初始化 conversation manager
        self._conversation_manager = self._create_conversation_manager()

    def _create_conversation_manager(self) -> BaseConversationManager:
        """创建 OpenCode 特定的对话管理器"""
        return OpenCodeConversationManager(
            worker_id=self.worker_id,
            db=self.db
        )

    async def start(self) -> bool:
        """
        启动 OpenCode worker

        注意：Worker 启动后不会立即创建进程，进程会在发送消息时按需创建
        """
        self.logger.info(f"OpenCode worker {self.worker_id} initialized successfully")
        return True

    async def _ensure_process_for_conversation(self, conversation_id: str) -> bool:
        """
        确保为指定对话创建进程

        Args:
            conversation_id: 对话 ID

        Returns:
            True if process is ready, False otherwise
        """
        conversation = await self._conversation_manager.get_conversation(conversation_id)
        if not conversation:
            self.logger.error(f"Conversation not found: {conversation_id}")
            return False

        project_path = conversation.project_path

        # 如果进程已经在运行，检查是否是同一个项目
        if self.process_handler and self.process_handler.is_alive():
            if self.process_handler.project_path == project_path:
                return True
            # 不同项目，需要停止当前进程
            await self._stop_process()

        # 创建并启动新进程
        try:
            def internal_output_callback(data: Dict[str, Any]):
                self._handle_output(data)

            self.process_handler = ProcessHandler(
                worker_id=self.worker_id,
                project_path=project_path,
                adapter=self.adapter,
                output_callback=internal_output_callback
            )

            success = await self.process_handler.start()
            if not success:
                self.logger.error(f"Failed to start process handler for worker {self.worker_id}")
                return False

            self.logger.info(f"Process started for worker {self.worker_id} at {project_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start process for worker {self.worker_id}: {e}")
            return False

    async def _stop_process(self) -> None:
        """停止当前进程"""
        if self.process_handler:
            await self.process_handler.stop()
            self.process_handler = None

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
            conversation_id: 对话 ID（必须提供，用于确定项目路径）

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            if not conversation_id:
                # 使用当前对话
                conversation_id = self._conversation_manager.get_current_conversation()
                if not conversation_id:
                    self.logger.error(f"No active conversation for worker {self.worker_id}")
                    return False

            # 切换对话（如果需要）
            current = self._conversation_manager.get_current_conversation()
            if current != conversation_id:
                await self._conversation_manager.switch_conversation(conversation_id)
                self.logger.info(f"Switched to conversation {conversation_id}")

            # 确保进程已经启动（根据对话的 project_path）
            if not await self._ensure_process_for_conversation(conversation_id):
                return False

            # 通过 ProcessHandler 发送消息
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
        current_conv_id = self._conversation_manager.get_current_conversation()
        current_project_path = None
        if current_conv_id:
            conv = await self._conversation_manager.get_conversation(current_conv_id)
            if conv:
                current_project_path = conv.project_path

        status = {
            "worker_id": self.worker_id,
            "type": "opencode",
            "current_project_path": current_project_path,
            "is_running": self.is_running(),
            "current_conversation": current_conv_id
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
