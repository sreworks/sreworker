"""File watcher service for monitoring log files."""

import asyncio
import os
from typing import Optional, Callable, Dict, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from ...utils.jsonl_parser import JSONLParser
from ...utils.logger import get_app_logger


class FileWatcherHandler(FileSystemEventHandler):
    """Handler for file system events."""

    def __init__(self, file_path: str, callback: Callable[[Dict[str, Any]], None]):
        """
        Initialize the file watcher handler.

        Args:
            file_path: Path to the file to watch
            callback: Callback function to call when new data is available
        """
        super().__init__()
        self.file_path = file_path
        self.callback = callback
        self.parser = JSONLParser(file_path)
        self.logger = get_app_logger()

    def on_modified(self, event):
        """
        Handle file modification event.

        Args:
            event: File system event
        """
        if isinstance(event, FileModifiedEvent) and event.src_path == self.file_path:
            # Run async task in event loop
            asyncio.create_task(self._process_new_lines())

    async def _process_new_lines(self):
        """Process new lines from the file."""
        try:
            new_lines = await self.parser.read_new_lines()

            for line_data in new_lines:
                try:
                    self.callback(line_data)
                except Exception as e:
                    self.logger.error(f"Error in file watcher callback: {e}")

        except Exception as e:
            self.logger.error(f"Error processing new lines: {e}")


class FileWatcher:
    """File watcher service for monitoring log files."""

    def __init__(
        self,
        file_path: str,
        callback: Callable[[Dict[str, Any]], None],
        adapter
    ):
        """
        Initialize the file watcher.

        Args:
            file_path: Path to the file to watch
            callback: Callback function to call when new data is available
            adapter: Adapter instance for parsing output
        """
        self.file_path = file_path
        self.callback = callback
        self.adapter = adapter
        self.observer: Optional[Observer] = None
        self.handler: Optional[FileWatcherHandler] = None
        self.logger = get_app_logger()
        self.is_running = False

    def start(self):
        """Start watching the file."""
        if self.is_running:
            self.logger.warning("File watcher is already running")
            return

        # Ensure the directory exists
        directory = os.path.dirname(self.file_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # Create the file if it doesn't exist
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                pass

        # Create handler with wrapped callback
        def wrapped_callback(line_data: Dict[str, Any]):
            """Wrapper to parse output through adapter."""
            try:
                # The line_data is already parsed JSON
                # Call the original callback
                self.callback(line_data)
            except Exception as e:
                self.logger.error(f"Error in wrapped callback: {e}")

        self.handler = FileWatcherHandler(self.file_path, wrapped_callback)

        # Create and start observer
        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            path=os.path.dirname(self.file_path),
            recursive=False
        )
        self.observer.start()
        self.is_running = True

        self.logger.info(f"File watcher started for: {self.file_path}")

    def stop(self):
        """Stop watching the file."""
        if not self.is_running:
            return

        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

        self.handler = None
        self.is_running = False

        self.logger.info(f"File watcher stopped for: {self.file_path}")

    def is_active(self) -> bool:
        """
        Check if the file watcher is active.

        Returns:
            True if the watcher is running, False otherwise
        """
        return self.is_running

    async def read_existing_content(self) -> None:
        """Read existing content from the file."""
        if not os.path.exists(self.file_path):
            return

        try:
            parser = JSONLParser(self.file_path)
            existing_lines = await parser.read_all_lines()

            for line_data in existing_lines:
                try:
                    self.callback(line_data)
                except Exception as e:
                    self.logger.error(f"Error processing existing line: {e}")

        except Exception as e:
            self.logger.error(f"Error reading existing content: {e}")
