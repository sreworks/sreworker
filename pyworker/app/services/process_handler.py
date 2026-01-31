"""Process handler service for managing AI CLI processes."""

import asyncio
import os
from typing import Optional, Callable, Dict, Any
from ..adapters.base import BaseWorkerAdapter
from ..utils.logger import get_app_logger


class ProcessHandler:
    """Handler for managing AI CLI subprocess."""

    def __init__(
        self,
        worker_id: str,
        project_path: str,
        adapter: BaseWorkerAdapter,
        output_callback: Callable[[Dict[str, Any]], None]
    ):
        """
        Initialize the process handler.

        Args:
            worker_id: Unique worker identifier
            project_path: Path to the project directory
            adapter: Adapter for the AI CLI
            output_callback: Callback function for processing output
        """
        self.worker_id = worker_id
        self.project_path = project_path
        self.adapter = adapter
        self.output_callback = output_callback
        self.process: Optional[asyncio.subprocess.Process] = None
        self.output_task: Optional[asyncio.Task] = None
        self.logger = get_app_logger()
        self.is_running = False

    async def start(self) -> bool:
        """
        Start the AI CLI process.

        Returns:
            True if process started successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning(f"Process for worker {self.worker_id} is already running")
            return False

        try:
            # Ensure project directory exists
            if not os.path.exists(self.project_path):
                os.makedirs(self.project_path, exist_ok=True)

            # Get command from adapter
            command = self.adapter.get_command(self.project_path)
            self.logger.info(f"Starting process with command: {' '.join(command)}")

            # Get environment variables from adapter
            env = os.environ.copy()
            env.update(self.adapter.get_env_vars())

            # Start the process
            self.process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_path,
                env=env
            )

            self.is_running = True
            self.logger.info(f"Process started for worker {self.worker_id} (PID: {self.process.pid})")

            # Start output reading task if adapter uses stdout
            if not self.adapter.needs_file_watcher():
                self.output_task = asyncio.create_task(self._read_stdout())

            return True

        except Exception as e:
            self.logger.error(f"Failed to start process for worker {self.worker_id}: {e}")
            self.is_running = False
            return False

    async def stop(self) -> None:
        """Stop the AI CLI process."""
        if not self.is_running:
            return

        try:
            # Cancel output reading task if running
            if self.output_task and not self.output_task.done():
                self.output_task.cancel()
                try:
                    await self.output_task
                except asyncio.CancelledError:
                    pass

            # Terminate the process
            if self.process:
                try:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if termination times out
                    self.process.kill()
                    await self.process.wait()

                self.logger.info(f"Process stopped for worker {self.worker_id}")

        except Exception as e:
            self.logger.error(f"Error stopping process for worker {self.worker_id}: {e}")

        finally:
            self.process = None
            self.output_task = None
            self.is_running = False

    async def send_message(self, message: str) -> bool:
        """
        Send a message to the AI CLI process.

        Args:
            message: Message to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.is_running or not self.process or not self.process.stdin:
            self.logger.error(f"Cannot send message: process not running for worker {self.worker_id}")
            return False

        try:
            # Format input through adapter
            formatted_message = self.adapter.format_input(message)

            # Write to stdin
            self.process.stdin.write(formatted_message.encode('utf-8'))
            await self.process.stdin.drain()

            self.logger.debug(f"Message sent to worker {self.worker_id}: {message[:100]}...")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send message to worker {self.worker_id}: {e}")
            return False

    async def _read_stdout(self) -> None:
        """Read output from stdout (for adapters that don't use file watching)."""
        if not self.process:
            return

        try:
            async for line in self.adapter.get_output_stream(self.process):
                if not line:
                    continue

                # Parse output through adapter
                parsed_output = self.adapter.parse_output(line)

                if parsed_output:
                    try:
                        # Call output callback
                        self.output_callback(parsed_output)
                    except Exception as e:
                        self.logger.error(f"Error in output callback: {e}")

        except asyncio.CancelledError:
            # Task was cancelled, clean up
            pass
        except Exception as e:
            self.logger.error(f"Error reading stdout for worker {self.worker_id}: {e}")

    def get_process_id(self) -> Optional[int]:
        """
        Get the process ID.

        Returns:
            Process ID, or None if process is not running
        """
        return self.process.pid if self.process else None

    def is_alive(self) -> bool:
        """
        Check if the process is still alive.

        Returns:
            True if process is running, False otherwise
        """
        if not self.is_running or not self.process:
            return False

        return self.process.returncode is None

    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the process.

        Returns:
            Dictionary with status information
        """
        return {
            "is_running": self.is_running,
            "is_alive": self.is_alive(),
            "pid": self.get_process_id(),
            "adapter_type": self.adapter.get_name(),
            "uses_file_watcher": self.adapter.needs_file_watcher()
        }
