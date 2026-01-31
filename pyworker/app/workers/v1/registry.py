"""Worker Registry - Worker 类注册和创建"""

from typing import Dict, Type, Any, Optional, Callable, TYPE_CHECKING
from .base import BaseWorker
from .claude import ClaudeCodeWorker
from .opencode import OpenCodeWorker
from ...utils.logger import get_app_logger

if TYPE_CHECKING:
    from ...services.v1.database import DatabaseManager


class WorkerRegistry:
    """Worker 类注册表"""

    def __init__(self):
        """初始化注册表"""
        self._workers: Dict[str, Type[BaseWorker]] = {}
        self.logger = get_app_logger()

        # 注册内置 workers
        self._register_builtin_workers()

    def _register_builtin_workers(self):
        """注册内置的 worker 类型"""
        self.register("claude", ClaudeCodeWorker)
        self.register("claudecode", ClaudeCodeWorker)  # 别名
        self.register("opencode", OpenCodeWorker)

    def register(self, name: str, worker_class: Type[BaseWorker]):
        """
        注册 worker 类

        Args:
            name: Worker 类型名称
            worker_class: Worker 类
        """
        name_lower = name.lower()
        self._workers[name_lower] = worker_class
        self.logger.info(f"Registered worker type: {name_lower} -> {worker_class.__name__}")

    def unregister(self, name: str):
        """
        取消注册 worker 类

        Args:
            name: Worker 类型名称
        """
        name_lower = name.lower()
        if name_lower in self._workers:
            del self._workers[name_lower]
            self.logger.info(f"Unregistered worker type: {name_lower}")

    def is_registered(self, name: str) -> bool:
        """
        检查 worker 类型是否已注册

        Args:
            name: Worker 类型名称

        Returns:
            True if registered, False otherwise
        """
        return name.lower() in self._workers

    def create_worker(
        self,
        name: str,
        worker_id: str,
        project_path: str,
        config: Dict[str, Any],
        output_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        db: Optional['DatabaseManager'] = None
    ) -> BaseWorker:
        """
        创建 worker 实例

        Args:
            name: Worker 类型名称
            worker_id: Worker ID
            project_path: 项目路径
            config: Worker 配置
            output_callback: 输出回调函数
            db: 数据库管理器（可选）

        Returns:
            Worker 实例

        Raises:
            ValueError: 如果 worker 类型未注册
        """
        name_lower = name.lower()

        if name_lower not in self._workers:
            raise ValueError(
                f"Unknown worker type: {name}. "
                f"Available types: {', '.join(self._workers.keys())}"
            )

        worker_class = self._workers[name_lower]

        # 创建 worker 实例
        worker = worker_class(
            worker_id=worker_id,
            project_path=project_path,
            config=config,
            output_callback=output_callback,
            db=db
        )

        self.logger.info(f"Created worker instance: {worker_id} (type: {name_lower})")

        return worker

    def list_registered_workers(self) -> Dict[str, str]:
        """
        列出所有已注册的 worker 类型

        Returns:
            字典，键为 worker 类型名称，值为 worker 类名
        """
        return {
            name: worker_class.__name__
            for name, worker_class in self._workers.items()
        }

    def get_worker_class(self, name: str) -> Optional[Type[BaseWorker]]:
        """
        获取 worker 类

        Args:
            name: Worker 类型名称

        Returns:
            Worker 类，如果未注册则返回 None
        """
        return self._workers.get(name.lower())


# 全局单例
worker_registry = WorkerRegistry()
