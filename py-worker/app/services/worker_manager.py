"""Worker manager service for managing multiple workers."""

import os
from datetime import datetime
from typing import Dict, Optional, List, Any, Set
from fastapi import WebSocket
from ..models.worker import WorkerModel, WorkerStatus, CreateWorkerRequest
from ..adapters.registry import adapter_registry
from ..adapters.base import BaseWorkerAdapter
from .process_handler import ProcessHandler
from .file_watcher import FileWatcher
from ..utils.logger import get_app_logger


class WorkerManager:
    """Manager for multiple AI Code workers."""

    def __init__(self, config):
        """
        Initialize the worker manager.

        Args:
            config: Application configuration
        """
        self.config = config
        self.workers: Dict[str, WorkerModel] = {}
        self.process_handlers: Dict[str, ProcessHandler] = {}
        self.file_watchers: Dict[str, FileWatcher] = {}
        self.websocket_connections: Dict[str, Set[WebSocket]] = {}
        self.message_history: Dict[str, List[Dict[str, Any]]] = {}
        self.logger = get_app_logger()

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
        if not adapter_registry.is_registered(request.ai_cli_type):
            raise ValueError(f"Unknown AI CLI type: {request.ai_cli_type}")

        # Create worker model
        worker = WorkerModel(
            name=request.name,
            project_path=os.path.abspath(request.project_path),
            ai_cli_type=request.ai_cli_type,
            config=request.config or {}
        )

        self.logger.info(f"Creating worker: {worker.id} ({worker.name}) with AI CLI: {worker.ai_cli_type}")

        try:
            # Get adapter
            adapter_config = {**self.config.get_ai_cli_config(worker.ai_cli_type), **worker.config}
            adapter = adapter_registry.get_adapter(worker.ai_cli_type, adapter_config)

            # Validate adapter configuration
            if not adapter.validate_config():
                raise ValueError(f"Invalid configuration for {worker.ai_cli_type}")

            # Create output callback
            def output_callback(data: Dict[str, Any]):
                self._handle_worker_output(worker.id, data)

            # Create process handler
            process_handler = ProcessHandler(
                worker_id=worker.id,
                project_path=worker.project_path,
                adapter=adapter,
                output_callback=output_callback
            )

            # Start the process
            success = await process_handler.start()
            if not success:
                raise RuntimeError("Failed to start AI CLI process")

            self.process_handlers[worker.id] = process_handler

            # Create file watcher if needed
            if adapter.needs_file_watcher():
                log_file_path = adapter.get_log_file_path(worker.project_path)
                if log_file_path:
                    file_watcher = FileWatcher(
                        file_path=log_file_path,
                        callback=output_callback,
                        adapter=adapter
                    )
                    file_watcher.start()
                    self.file_watchers[worker.id] = file_watcher

                    self.logger.info(f"File watcher started for worker {worker.id}")

            # Update worker status
            worker.status = WorkerStatus.RUNNING
            worker.last_activity = datetime.utcnow()

            # Store worker
            self.workers[worker.id] = worker
            self.message_history[worker.id] = []
            self.websocket_connections[worker.id] = set()

            self.logger.info(f"Worker created successfully: {worker.id}")

            return worker

        except Exception as e:
            self.logger.error(f"Failed to create worker: {e}")
            # Cleanup on failure
            if worker.id in self.process_handlers:
                await self.process_handlers[worker.id].stop()
                del self.process_handlers[worker.id]
            if worker.id in self.file_watchers:
                self.file_watchers[worker.id].stop()
                del self.file_watchers[worker.id]
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
            # Stop process handler
            if worker_id in self.process_handlers:
                await self.process_handlers[worker_id].stop()
                del self.process_handlers[worker_id]

            # Stop file watcher
            if worker_id in self.file_watchers:
                self.file_watchers[worker_id].stop()
                del self.file_watchers[worker_id]

            # Close WebSocket connections
            if worker_id in self.websocket_connections:
                for ws in self.websocket_connections[worker_id]:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                del self.websocket_connections[worker_id]

            # Remove worker data
            del self.workers[worker_id]
            if worker_id in self.message_history:
                del self.message_history[worker_id]

            self.logger.info(f"Worker deleted: {worker_id}")

        except Exception as e:
            self.logger.error(f"Error deleting worker {worker_id}: {e}")
            raise

    def get_worker(self, worker_id: str) -> Optional[WorkerModel]:
        """
        Get a worker by ID.

        Args:
            worker_id: Worker ID

        Returns:
            Worker model, or None if not found
        """
        return self.workers.get(worker_id)

    def list_workers(self) -> List[WorkerModel]:
        """
        List all workers.

        Returns:
            List of worker models
        """
        return list(self.workers.values())

    async def send_message(self, worker_id: str, message: str) -> bool:
        """
        Send a message to a worker.

        Args:
            worker_id: Worker ID
            message: Message to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        if worker_id not in self.workers:
            self.logger.error(f"Worker not found: {worker_id}")
            return False

        if worker_id not in self.process_handlers:
            self.logger.error(f"Process handler not found for worker: {worker_id}")
            return False

        # Send message to process
        success = await self.process_handlers[worker_id].send_message(message)

        if success:
            # Update last activity
            self.workers[worker_id].last_activity = datetime.utcnow()

            # Store message in history
            self.message_history[worker_id].append({
                "type": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            })

        return success

    def _handle_worker_output(self, worker_id: str, data: Dict[str, Any]) -> None:
        """
        Handle output from a worker.

        Args:
            worker_id: Worker ID
            data: Output data
        """
        # Update last activity
        if worker_id in self.workers:
            self.workers[worker_id].last_activity = datetime.utcnow()

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
        if worker_id not in self.workers:
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
