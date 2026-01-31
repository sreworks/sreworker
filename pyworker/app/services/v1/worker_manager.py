"""Worker manager service for managing workers and conversations - V1"""

import os
from datetime import datetime
from typing import Dict, Optional, List, Any, Set
from fastapi import WebSocket
import uuid

from ...models.v1.worker import WorkerModel, CreateWorkerRequest
from ...workers import handlers
from ...workers.v1 import BaseWorker
from ...utils.logger import get_app_logger
from .database import DatabaseManager
from .process_handler import ProcessHandler


class WorkerManager:
    """Manager for workers (DB records) and conversations (runtime)"""

    def __init__(self, config):
        self.config = config
        self.logger = get_app_logger()

        # 运行中的 conversation 实例 {conversation_id: ConversationRunner}
        self.conversations: Dict[str, 'ConversationRunner'] = {}

        # WebSocket 连接 {conversation_id: Set[WebSocket]}
        self.websocket_connections: Dict[str, Set[WebSocket]] = {}

        # Initialize database
        self.db: Optional[DatabaseManager] = None
        if config.enable_database:
            try:
                self.db = DatabaseManager(config.database_path)
                self.logger.info(f"Database enabled at {config.database_path}")
            except Exception as e:
                self.logger.error(f"Failed to initialize database: {e}")
                self.logger.warning("Running without database persistence")

    # === Worker 方法 (纯数据库操作) ===

    def create_worker(self, request: CreateWorkerRequest) -> WorkerModel:
        """创建 worker (只写数据库)"""
        worker_type = request.type.lower()
        if worker_type not in handlers:
            raise ValueError(
                f"Unknown worker type: {request.type}. "
                f"Available: {list(handlers.keys())}"
            )

        worker_id = str(uuid.uuid4())

        worker_model = WorkerModel(
            id=worker_id,
            type=worker_type,
            env_vars=request.env_vars or {},
            command_params=request.command_params or []
        )

        if self.db:
            self.db.create_worker({
                'id': worker_model.id,
                'type': worker_model.type,
                'env_vars': worker_model.env_vars,
                'command_params': worker_model.command_params,
                'created_at': worker_model.created_at
            })

        self.logger.info(f"Worker created: {worker_id} (type: {worker_type})")
        return worker_model

    def get_worker(self, worker_id: str) -> Optional[WorkerModel]:
        """获取 worker (从数据库)"""
        if not self.db:
            return None

        data = self.db.get_worker(worker_id)
        if not data:
            return None

        return WorkerModel(
            id=data['id'],
            type=data['type'],
            env_vars=data.get('env_vars', {}),
            command_params=data.get('command_params', []),
            created_at=data.get('created_at', datetime.utcnow())
        )

    def list_workers(self) -> List[WorkerModel]:
        """列出所有 workers (从数据库)"""
        if not self.db:
            return []

        workers_data = self.db.list_workers()
        return [
            WorkerModel(
                id=data['id'],
                type=data['type'],
                env_vars=data.get('env_vars', {}),
                command_params=data.get('command_params', []),
                created_at=data.get('created_at', datetime.utcnow())
            )
            for data in workers_data
        ]

    def delete_worker(self, worker_id: str) -> None:
        """删除 worker (从数据库)"""
        if not self.db:
            raise ValueError("Database not available")

        # 检查 worker 是否存在
        if not self.db.get_worker(worker_id):
            raise ValueError(f"Worker not found: {worker_id}")

        # 停止该 worker 下所有运行中的 conversations
        conversations_to_stop = [
            conv_id for conv_id, runner in self.conversations.items()
            if runner.worker_id == worker_id
        ]
        for conv_id in conversations_to_stop:
            self._stop_conversation(conv_id)

        self.db.delete_worker(worker_id)
        self.logger.info(f"Worker deleted: {worker_id}")

    # === Conversation 方法 ===

    async def new_conversation(self, worker_id: str, project_path: str, name: Optional[str] = None) -> str:
        """创建新对话并启动进程"""
        worker = self.get_worker(worker_id)
        if not worker:
            raise ValueError(f"Worker not found: {worker_id}")

        conversation_id = str(uuid.uuid4())
        project_path = os.path.abspath(project_path)
        conv_name = name or f"Conversation {conversation_id[:8]}"

        # 保存到数据库
        if self.db:
            self.db.create_conversation({
                'id': conversation_id,
                'worker_id': worker_id,
                'project_path': project_path,
                'name': conv_name,
                'created_at': datetime.utcnow(),
                'last_activity': datetime.utcnow(),
                'is_current': True,
                'metadata': {}
            })

        # 创建并启动 conversation runner
        runner = ConversationRunner(
            conversation_id=conversation_id,
            worker_id=worker_id,
            worker_type=worker.type,
            project_path=project_path,
            env_vars=worker.env_vars,
            command_params=worker.command_params,
            output_callback=lambda data: self._handle_output(conversation_id, data),
            logger=self.logger
        )
        await runner.start()
        self.conversations[conversation_id] = runner

        self.logger.info(f"Conversation created and started: {conversation_id}")
        return conversation_id

    async def list_conversations(self, worker_id: str) -> List[Dict[str, Any]]:
        """列出 worker 的所有对话"""
        if not self.db:
            return []

        # 检查 worker 是否存在
        if not self.db.get_worker(worker_id):
            raise ValueError(f"Worker not found: {worker_id}")

        conversations = self.db.list_conversations(worker_id)
        return [
            {
                'id': c['id'],
                'name': c['name'],
                'project_path': c['project_path'],
                'created_at': c['created_at'].isoformat() if c.get('created_at') else None,
                'last_activity': c['last_activity'].isoformat() if c.get('last_activity') else None,
                'is_running': c['id'] in self.conversations,
                'metadata': c.get('metadata', {})
            }
            for c in conversations
        ]

    async def get_conversation(self, worker_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取对话详情"""
        if not self.db:
            return None

        conv = self.db.get_conversation(conversation_id)
        if not conv or conv.get('worker_id') != worker_id:
            return None

        return {
            'id': conv['id'],
            'name': conv['name'],
            'project_path': conv['project_path'],
            'created_at': conv['created_at'].isoformat() if conv.get('created_at') else None,
            'last_activity': conv['last_activity'].isoformat() if conv.get('last_activity') else None,
            'is_running': conv['id'] in self.conversations,
            'metadata': conv.get('metadata', {})
        }

    async def delete_conversation(self, worker_id: str, conversation_id: str) -> bool:
        """删除对话"""
        if not self.db:
            return False

        conv = self.db.get_conversation(conversation_id)
        if not conv or conv.get('worker_id') != worker_id:
            return False

        # 停止运行中的 conversation
        if conversation_id in self.conversations:
            await self._stop_conversation(conversation_id)

        self.db.delete_conversation(conversation_id)
        self.logger.info(f"Conversation deleted: {conversation_id}")
        return True

    async def start_conversation(self, worker_id: str, conversation_id: str) -> bool:
        """启动已有的对话"""
        if conversation_id in self.conversations:
            return True  # 已经在运行

        worker = self.get_worker(worker_id)
        if not worker:
            raise ValueError(f"Worker not found: {worker_id}")

        if not self.db:
            raise ValueError("Database not available")

        conv = self.db.get_conversation(conversation_id)
        if not conv or conv.get('worker_id') != worker_id:
            raise ValueError(f"Conversation not found: {conversation_id}")

        runner = ConversationRunner(
            conversation_id=conversation_id,
            worker_id=worker_id,
            worker_type=worker.type,
            project_path=conv['project_path'],
            env_vars=worker.env_vars,
            command_params=worker.command_params,
            output_callback=lambda data: self._handle_output(conversation_id, data),
            logger=self.logger
        )
        await runner.start()
        self.conversations[conversation_id] = runner

        self.logger.info(f"Conversation started: {conversation_id}")
        return True

    async def stop_conversation(self, worker_id: str, conversation_id: str) -> bool:
        """停止对话"""
        if conversation_id not in self.conversations:
            return False

        await self._stop_conversation(conversation_id)
        return True

    async def send_message(self, worker_id: str, conversation_id: str, message: str) -> bool:
        """发送消息到对话"""
        if conversation_id not in self.conversations:
            # 尝试启动 conversation
            await self.start_conversation(worker_id, conversation_id)

        runner = self.conversations.get(conversation_id)
        if not runner:
            self.logger.error(f"Conversation not running: {conversation_id}")
            return False

        success = await runner.send_message(message)

        if success and self.db:
            self.db.add_message({
                'conversation_id': conversation_id,
                'worker_id': worker_id,
                'role': 'user',
                'content': message,
                'timestamp': datetime.utcnow(),
                'metadata': {}
            })

        return success

    async def get_conversation_messages(self, worker_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话消息"""
        if not self.db:
            return []
        return self.db.get_conversation_messages(conversation_id)

    async def clone_conversation(self, worker_id: str, conversation_id: str, new_name: Optional[str] = None) -> str:
        """克隆对话"""
        if not self.db:
            raise ValueError("Database not available")

        conv = self.db.get_conversation(conversation_id)
        if not conv or conv.get('worker_id') != worker_id:
            raise ValueError(f"Conversation not found: {conversation_id}")

        new_id = str(uuid.uuid4())
        clone_name = new_name or f"{conv['name']} (copy)"

        self.db.create_conversation({
            'id': new_id,
            'worker_id': worker_id,
            'project_path': conv['project_path'],
            'name': clone_name,
            'created_at': datetime.utcnow(),
            'last_activity': datetime.utcnow(),
            'is_current': False,
            'metadata': conv.get('metadata', {})
        })

        self.logger.info(f"Conversation cloned: {conversation_id} -> {new_id}")
        return new_id

    async def switch_conversation(self, worker_id: str, conversation_id: str) -> bool:
        """切换当前对话"""
        if not self.db:
            raise ValueError("Database not available")

        conv = self.db.get_conversation(conversation_id)
        if not conv or conv.get('worker_id') != worker_id:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # 将所有对话设为非当前，然后设置指定对话为当前
        self.db.switch_conversation(worker_id, conversation_id)
        self.logger.info(f"Switched to conversation: {conversation_id}")
        return True

    async def rename_conversation(self, worker_id: str, conversation_id: str, new_name: str) -> bool:
        """重命名对话"""
        if not self.db:
            return False

        conv = self.db.get_conversation(conversation_id)
        if not conv or conv.get('worker_id') != worker_id:
            return False

        self.db.update_conversation(conversation_id, {'name': new_name})
        self.logger.info(f"Conversation renamed: {conversation_id} -> {new_name}")
        return True

    def get_current_conversation(self, worker_id: str) -> Optional[str]:
        """获取当前对话 ID"""
        if not self.db:
            return None

        # 检查 worker 是否存在
        if not self.db.get_worker(worker_id):
            raise ValueError(f"Worker not found: {worker_id}")

        return self.db.get_current_conversation(worker_id)

    # === 内部方法 ===

    async def _stop_conversation(self, conversation_id: str) -> None:
        """停止 conversation"""
        runner = self.conversations.pop(conversation_id, None)
        if runner:
            await runner.stop()

        # 关闭 WebSocket 连接
        if conversation_id in self.websocket_connections:
            for ws in self.websocket_connections[conversation_id]:
                try:
                    await ws.close()
                except Exception:
                    pass
            del self.websocket_connections[conversation_id]

    def _handle_output(self, conversation_id: str, data: Dict[str, Any]) -> None:
        """处理 conversation 输出"""
        # 广播到 WebSocket
        if conversation_id in self.websocket_connections:
            import asyncio
            for ws in list(self.websocket_connections[conversation_id]):
                try:
                    asyncio.create_task(ws.send_json({
                        "type": "output",
                        "conversation_id": conversation_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "content": data
                    }))
                except Exception as e:
                    self.logger.error(f"Error sending to WebSocket: {e}")
                    self.websocket_connections[conversation_id].discard(ws)

    async def register_websocket(self, conversation_id: str, websocket: WebSocket) -> None:
        """注册 WebSocket 连接"""
        if conversation_id not in self.websocket_connections:
            self.websocket_connections[conversation_id] = set()
        self.websocket_connections[conversation_id].add(websocket)

    async def unregister_websocket(self, conversation_id: str, websocket: WebSocket) -> None:
        """注销 WebSocket 连接"""
        if conversation_id in self.websocket_connections:
            self.websocket_connections[conversation_id].discard(websocket)

    async def shutdown(self) -> None:
        """关闭所有 conversations"""
        self.logger.info("Shutting down all conversations...")
        for conv_id in list(self.conversations.keys()):
            await self._stop_conversation(conv_id)
        self.logger.info("All conversations shut down")


class ConversationRunner:
    """运行中的 conversation 实例"""

    def __init__(
        self,
        conversation_id: str,
        worker_id: str,
        worker_type: str,
        project_path: str,
        env_vars: Dict[str, str],
        command_params: List[str],
        output_callback,
        logger
    ):
        self.conversation_id = conversation_id
        self.worker_id = worker_id
        self.worker_type = worker_type
        self.project_path = project_path
        self.env_vars = env_vars
        self.command_params = command_params
        self.output_callback = output_callback
        self.logger = logger
        self.process_handler: Optional[ProcessHandler] = None

    async def start(self) -> bool:
        """启动进程"""
        from ...adapters.v1 import adapter_registry

        adapter = adapter_registry.get_adapter(self.worker_type)
        if not adapter:
            self.logger.error(f"Adapter not found for type: {self.worker_type}")
            return False

        self.process_handler = ProcessHandler(
            worker_id=self.conversation_id,  # 使用 conversation_id 作为标识
            project_path=self.project_path,
            adapter=adapter,
            output_callback=self.output_callback
        )

        success = await self.process_handler.start()
        if success:
            self.logger.info(f"Process started for conversation: {self.conversation_id}")
        return success

    async def stop(self) -> None:
        """停止进程"""
        if self.process_handler:
            await self.process_handler.stop()
            self.process_handler = None
            self.logger.info(f"Process stopped for conversation: {self.conversation_id}")

    async def send_message(self, message: str) -> bool:
        """发送消息"""
        if not self.process_handler:
            return False
        return await self.process_handler.send_message(message)

    def is_running(self) -> bool:
        """检查是否运行中"""
        return self.process_handler is not None and self.process_handler.is_alive()
