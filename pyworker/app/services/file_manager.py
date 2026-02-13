"""通用文件监控服务，基于 watchfiles（async 原生）"""

import asyncio
import logging
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from watchfiles import awatch, Change

FileChangeCallback = Callable[[Path], Awaitable[None]]

logger = logging.getLogger(__name__)


class FileManager:
    """通用文件监控服务，基于 watchfiles（Rust notify，原生 async）"""

    def __init__(self):
        self._watches: Dict[str, List[FileChangeCallback]] = {}  # abs_path -> [callbacks]
        self._dir_watches: Dict[str, List[FileChangeCallback]] = {}  # dir_path -> [callbacks]
        self._dir_tasks: Dict[str, asyncio.Task] = {}  # dir_path -> watch task
        self._stop_event: Optional[asyncio.Event] = None
        self._running = False

    def start(self):
        """标记为运行状态"""
        self._stop_event = asyncio.Event()
        self._running = True
        logger.info("[FileManager] started")

    def watch_directory(self, dir_path: str | Path, callback: FileChangeCallback):
        """监控整个目录（递归）。callback 收到每个变更文件的 Path。"""
        abs_dir = str(Path(dir_path).resolve())
        if abs_dir not in self._dir_watches:
            self._dir_watches[abs_dir] = []
        self._dir_watches[abs_dir].append(callback)
        logger.info(f"[FileManager] watching directory: {abs_dir}")

        if abs_dir not in self._dir_tasks and self._running:
            task = asyncio.create_task(self._dir_watch_loop(abs_dir))
            self._dir_tasks[abs_dir] = task
            logger.info(f"[FileManager] started dir watch loop for: {abs_dir}")

    def unwatch_directory(self, dir_path: str | Path, callback: FileChangeCallback = None):
        """取消目录监控。如果 callback 为 None，移除该目录所有回调。"""
        abs_dir = str(Path(dir_path).resolve())

        if abs_dir not in self._dir_watches:
            return

        if callback is None:
            del self._dir_watches[abs_dir]
        else:
            self._dir_watches[abs_dir] = [cb for cb in self._dir_watches[abs_dir] if cb is not callback]
            if not self._dir_watches[abs_dir]:
                del self._dir_watches[abs_dir]

        logger.info(f"[FileManager] unwatched directory: {abs_dir}")

        # 如果该目录不再有回调且不再有文件级 watch，取消 task
        has_file_watches = any(
            str(Path(p).parent) == abs_dir for p in self._watches
        )
        if abs_dir not in self._dir_watches and not has_file_watches and abs_dir in self._dir_tasks:
            self._dir_tasks[abs_dir].cancel()
            del self._dir_tasks[abs_dir]
            logger.info(f"[FileManager] stopped dir watch loop for: {abs_dir}")

    def stop(self):
        """取消所有 watch task，设置 stop_event"""
        self._running = False
        if self._stop_event:
            self._stop_event.set()
        for dir_path, task in self._dir_tasks.items():
            task.cancel()
            logger.debug(f"[FileManager] cancelled watch task for dir: {dir_path}")
        self._dir_tasks.clear()
        self._watches.clear()
        self._dir_watches.clear()
        logger.info("[FileManager] stopped")

    def watch(self, file_path: str | Path, callback: FileChangeCallback):
        """注册文件监控。如果文件所在目录尚未监控，启动新的 _watch_loop task"""
        abs_path = str(Path(file_path).resolve())
        dir_path = str(Path(abs_path).parent)

        if abs_path not in self._watches:
            self._watches[abs_path] = []
        self._watches[abs_path].append(callback)
        logger.info(f"[FileManager] watching file: {abs_path}")

        # 如果目录尚未监控，启动新的 watch loop
        if dir_path not in self._dir_tasks and self._running:
            task = asyncio.create_task(self._watch_loop(dir_path))
            self._dir_tasks[dir_path] = task
            logger.info(f"[FileManager] started watch loop for dir: {dir_path}")

    def unwatch(self, file_path: str | Path, callback: FileChangeCallback = None):
        """取消监控。如果 callback 为 None，移除该文件所有回调。
        如果目录下无任何文件监控，取消对应 task"""
        abs_path = str(Path(file_path).resolve())
        dir_path = str(Path(abs_path).parent)

        if abs_path not in self._watches:
            return

        if callback is None:
            del self._watches[abs_path]
        else:
            self._watches[abs_path] = [cb for cb in self._watches[abs_path] if cb is not callback]
            if not self._watches[abs_path]:
                del self._watches[abs_path]

        logger.info(f"[FileManager] unwatched file: {abs_path}")

        # 检查目录下是否还有文件监控
        has_watches_in_dir = any(
            str(Path(p).parent) == dir_path for p in self._watches
        )
        if not has_watches_in_dir and dir_path in self._dir_tasks:
            self._dir_tasks[dir_path].cancel()
            del self._dir_tasks[dir_path]
            logger.info(f"[FileManager] stopped watch loop for dir: {dir_path}")

    async def _watch_loop(self, dir_path: str):
        """单个目录的监控循环"""
        try:
            async for changes in awatch(dir_path, stop_event=self._stop_event):
                for change_type, changed_path in changes:
                    abs_changed = str(Path(changed_path).resolve())
                    if abs_changed in self._watches:
                        for cb in list(self._watches[abs_changed]):
                            try:
                                await cb(Path(abs_changed))
                            except Exception:
                                logger.exception(
                                    f"[FileManager] callback error for {abs_changed}"
                                )
        except asyncio.CancelledError:
            logger.debug(f"[FileManager] watch loop cancelled for dir: {dir_path}")
        except Exception:
            logger.exception(f"[FileManager] watch loop error for dir: {dir_path}")

    async def _dir_watch_loop(self, dir_path: str):
        """目录级监控循环：所有变更都派发给 callback（由 callback 自行过滤）"""
        try:
            async for changes in awatch(dir_path, stop_event=self._stop_event):
                for change_type, changed_path in changes:
                    for cb in list(self._dir_watches.get(dir_path, [])):
                        try:
                            await cb(Path(changed_path))
                        except Exception:
                            logger.exception(
                                f"[FileManager] dir callback error for {changed_path}"
                            )
        except asyncio.CancelledError:
            logger.debug(f"[FileManager] dir watch loop cancelled for: {dir_path}")
        except Exception:
            logger.exception(f"[FileManager] dir watch loop error for: {dir_path}")
