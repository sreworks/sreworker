"""Worker manager service for managing multiple workers - V1"""

import os
from datetime import datetime
from typing import Dict, Optional, List, Any, Set
from fastapi import WebSocket
import uuid

from ...models.v1.worker import WorkerModel, WorkerStatus, CreateWorkerRequest
from ...workers.v1.registry import worker_registry
from ...workers.v1.base import BaseWorker
from ...utils.logger import get_app_logger
from .database import DatabaseManager


class WorkerManager:
    """Manager for multiple AI Code workers - V1 implementation"""

    def __init__(self, config):
        """
        Initialize the worker manager.

        Args:
            config: Application configuration
        """
        self.config = config
        self.workers: Dict[str, BaseWorker] = {}
        self.worker_models: Dict[str, WorkerModel] = {}
        self.websocket_connections: Dict[str, Set[WebSocket]] = {}
        self.message_history: Dict[str, List[Dict[str, Any]]] = {}
        self.logger = get_app_logger()

        # Initialize database
        self.db: Optional[DatabaseManager] = None
        if config.enable_database:
            try:
                self.db = DatabaseManager(config.database_path)
                self.logger.info(f"Database enabled at {config.database_path}")
            except Exception as e:
                self.logger.error(f"Failed to initialize database: {e}")
                self.logger.warning("Running without database persistence")

    async def create_worker(self, request: CreateWorkerRequest) -> WorkerModel:
        """
        Create a new worker.

        Args:
            request: Worker creation request

        Returns:
            Created worker model

        Raises:
            ValueError: If worker creation fails
        """
        # Check max workers limit
        if len(self.workers) >= self.config.max_workers:
            raise ValueError(f"Maximum number of workers ({self.config.max_workers}) reached")

        # Validate AI CLI type
        if not worker_registry.is_registered(request.type):
            available_types = ', '.join(worker_registry.list_registered_workers().keys())
            raise ValueError(
                f"Unknown AI CLI type: {request.type}. "
                f"Available types: {available_types}"
            )

        worker_id = str(uuid.uuid4())

        self.logger.info(f"Creating worker: {worker_id} with type: {request.type}")

        try:
            # 创建输出回调
            def output_callback(data: Dict[str, Any]):
                self._handle_worker_output(worker_id, data)

            # 构建 worker config
            worker_config = {
                'env_vars': request.env_vars or {},
                'command_params': request.command_params or []
            }

            # 通过 registry 创建 worker
            worker = worker_registry.create_worker(
                name=request.type,
                worker_id=worker_id,
                config=worker_config,
                output_callback=output_callback,
                db=self.db
            )

            # 启动 worker
            success = await worker.start()
            if not success:
                raise RuntimeError("Failed to start worker")

            # 创建 worker model
            worker_model = WorkerModel(
                id=worker_id,
                type=request.type,
                env_vars=request.env_vars or {},
                command_params=request.command_params or [],
                status=WorkerStatus.RUNNING,
                last_activity=datetime.utcnow()
            )

            # 存储到内存
            self.workers[worker_id] = worker
            self.worker_models[worker_id] = worker_model
            self.message_history[worker_id] = []
            self.websocket_connections[worker_id] = set()

            # 保存到数据库
            if self.db:
                worker_data = {
                    'id': worker_model.id,
                    'type': worker_model.type,
                    'env_vars': worker_model.env_vars,
                    'command_params': worker_model.command_params,
                    'status': worker_model.status.value,
                    'created_at': worker_model.created_at,
                    'last_activity': worker_model.last_activity
                }
                self.db.create_worker(worker_data)

            self.logger.info(f"Worker created successfully: {worker_id}")

            return worker_model

        except Exception as e:
            self.logger.error(f"Failed to create worker: {e}")
            # Cleanup on failure
            if worker_id in self.workers:
                try:
                    await self.workers[worker_id].stop()
                except Exception:
                    pass
                del self.workers[worker_id]
            if worker_id in self.worker_models:
                del self.worker_models[worker_id]
            raise ValueError(f"Failed to create worker: {e}")

    async def delete_worker(self, worker_id: str) -> None:
        """
        Delete a worker.

        Args:
            worker_id: Worker ID to delete

        Raises:
            ValueError: If worker not found
        """
        if worker_id not in self.workers:
            raise ValueError(f"Worker not found: {worker_id}")

        self.logger.info(f"Deleting worker: {worker_id}")

        try:
            # Stop worker
            worker = self.workers[worker_id]
            await worker.stop()

            # Close WebSocket connections
            if worker_id in self.websocket_connections:
                for ws in self.websocket_connections[worker_id]:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                del self.websocket_connections[worker_id]

            # Remove from database
            if self.db:
                self.db.delete_worker(worker_id)

            # Remove worker data from memory
            del self.workers[worker_id]
            del self.worker_models[worker_id]
            if worker_id in self.message_history:
                del self.message_history[worker_id]

            self.logger.info(f"Worker deleted: {worker_id}")

        except Exception as e:
            self.logger.error(f"Error deleting worker {worker_id}: {e}")
            raise

    def get_worker(self, worker_id: str) -> Optional[WorkerModel]:
        """
        Get a worker model by ID.

        Args:
            worker_id: Worker ID

        Returns:
            Worker model, or None if not found
        """
        return self.worker_models.get(worker_id)

    def get_worker_instance(self, worker_id: str) -> Optional[BaseWorker]:
        """
        Get a worker instance by ID.

        Args:
            worker_id: Worker ID

        Returns:
            Worker instance, or None if not found
        """
        return self.workers.get(worker_id)

    def list_workers(self) -> List[WorkerModel]:
        """
        List all workers.

        Returns:
            List of worker models
        """
        return list(self.worker_models.values())

    async def send_message(self, worker_id: str, message: str, conversation_id: Optional[str] = None) -> bool:
        """
        Send a message to a worker.

        Args:
            worker_id: Worker ID
            message: Message to send
            conversation_id: Optional conversation ID

        Returns:
            True if message was sent successfully, False otherwise
        """
        if worker_id not in self.workers:
            self.logger.error(f"Worker not found: {worker_id}")
            return False

        worker = self.workers[worker_id]

        # Send message to worker
        success = await worker.send_message(message, conversation_id)

        if success:
            timestamp = datetime.utcnow()

            # Update last activity
            if worker_id in self.worker_models:
                self.worker_models[worker_id].last_activity = timestamp

                # Update in database
                if self.db:
                    self.db.update_worker_status(worker_id, WorkerStatus.RUNNING.value, timestamp)

            # Store message in history (memory)
            message_data = {
                "type": "user",
                "content": message,
                "conversation_id": conversation_id,
                "timestamp": timestamp.isoformat()
            }
            self.message_history[worker_id].append(message_data)

            # Save to database
            if self.db and conversation_id:
                self.db.add_message({
                    'conversation_id': conversation_id,
                    'worker_id': worker_id,
                    'role': 'user',
                    'content': message,
                    'timestamp': timestamp,
                    'metadata': {}
                })

        return success

    # === Conversation 相关方法 ===

    async def new_conversation(self, worker_id: str, project_path: str, name: Optional[str] = None) -> str:
        """创建新对话"""
        worker = self._get_worker_instance(worker_id)
        conversation_manager = worker.get_conversation_manager()
        return await conversation_manager.new_conversation(project_path, name)

    async def clone_conversation(self, worker_id: str, conversation_id: str, new_name: Optional[str] = None) -> str:
        """克隆对话"""
        worker = self._get_worker_instance(worker_id)
        conversation_manager = worker.get_conversation_manager()
        return await conversation_manager.clone_conversation(conversation_id, new_name)

    async def list_conversations(self, worker_id: str) -> List[Dict[str, Any]]:
        """列出对话"""
        worker = self._get_worker_instance(worker_id)
        conversation_manager = worker.get_conversation_manager()
        conversations = await conversation_manager.list_conversations()
        return [c.to_dict() for c in conversations]

    async def get_conversation(self, worker_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取指定对话"""
        worker = self._get_worker_instance(worker_id)
        conversation_manager = worker.get_conversation_manager()
        conversation = await conversation_manager.get_conversation(conversation_id)
        return conversation.to_dict() if conversation else None

    async def delete_conversation(self, worker_id: str, conversation_id: str) -> bool:
        """删除对话"""
        worker = self._get_worker_instance(worker_id)
        conversation_manager = worker.get_conversation_manager()
        return await conversation_manager.delete_conversation(conversation_id)

    async def switch_conversation(self, worker_id: str, conversation_id: str) -> bool:
        """切换对话"""
        worker = self._get_worker_instance(worker_id)
        conversation_manager = worker.get_conversation_manager()
        return await conversation_manager.switch_conversation(conversation_id)

    async def rename_conversation(self, worker_id: str, conversation_id: str, new_name: str) -> bool:
        """重命名对话"""
        worker = self._get_worker_instance(worker_id)
        conversation_manager = worker.get_conversation_manager()
        return await conversation_manager.rename_conversation(conversation_id, new_name)

    async def get_conversation_messages(self, worker_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话消息历史"""
        worker = self._get_worker_instance(worker_id)
        conversation_manager = worker.get_conversation_manager()
        return await conversation_manager.get_conversation_messages(conversation_id)

    def get_current_conversation(self, worker_id: str) -> Optional[str]:
        """获取当前对话 ID"""
        worker = self._get_worker_instance(worker_id)
        conversation_manager = worker.get_conversation_manager()
        return conversation_manager.get_current_conversation()

    def _get_worker_instance(self, worker_id: str) -> BaseWorker:
        """获取 worker 实例（内部方法）"""
        if worker_id not in self.workers:
            raise ValueError(f"Worker not found: {worker_id}")
        return self.workers[worker_id]

    def _handle_worker_output(self, worker_id: str, data: Dict[str, Any]) -> None:
        """
        Handle output from a worker.

        Args:
            worker_id: Worker ID
            data: Output data
        """
        # Update last activity
        if worker_id in self.worker_models:
            self.worker_models[worker_id].last_activity = datetime.utcnow()

        # Store in message history
        if worker_id in self.message_history:
            self.message_history[worker_id].append({
                **data,
                "timestamp": datetime.utcnow().isoformat()
            })

        # Broadcast to WebSocket connections
        if worker_id in self.websocket_connections:
            import asyncio
            for ws in list(self.websocket_connections[worker_id]):
                try:
                    asyncio.create_task(ws.send_json({
                        "type": "output",
                        "timestamp": datetime.utcnow().isoformat(),
                        "content": data
                    }))
                except Exception as e:
                    self.logger.error(f"Error sending to WebSocket: {e}")
                    # Remove failed connection
                    self.websocket_connections[worker_id].discard(ws)

    async def register_websocket(self, worker_id: str, websocket: WebSocket) -> None:
        """
        Register a WebSocket connection for a worker.

        Args:
            worker_id: Worker ID
            websocket: WebSocket connection
        """
        if worker_id not in self.worker_models:
            raise ValueError(f"Worker not found: {worker_id}")

        if worker_id not in self.websocket_connections:
            self.websocket_connections[worker_id] = set()

        self.websocket_connections[worker_id].add(websocket)
        self.logger.info(f"WebSocket registered for worker: {worker_id}")

    async def unregister_websocket(self, worker_id: str, websocket: WebSocket) -> None:
        """
        Unregister a WebSocket connection for a worker.

        Args:
            worker_id: Worker ID
            websocket: WebSocket connection
        """
        if worker_id in self.websocket_connections:
            self.websocket_connections[worker_id].discard(websocket)
            self.logger.info(f"WebSocket unregistered for worker: {worker_id}")

    def get_message_history(self, worker_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get message history for a worker.

        Args:
            worker_id: Worker ID
            limit: Maximum number of messages to return

        Returns:
            List of messages
        """
        if worker_id not in self.message_history:
            return []

        history = self.message_history[worker_id]
        return history[-limit:] if len(history) > limit else history

    async def shutdown(self) -> None:
        """Shutdown all workers."""
        self.logger.info("Shutting down all workers...")

        worker_ids = list(self.workers.keys())
        for worker_id in worker_ids:
            try:
                await self.delete_worker(worker_id)
            except Exception as e:
                self.logger.error(f"Error shutting down worker {worker_id}: {e}")

        self.logger.info("All workers shut down")
