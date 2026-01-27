"""Base adapter for AI CLI integration."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncIterator
import asyncio


class BaseWorkerAdapter(ABC):
    """
    Abstract base class for AI CLI adapters.

    This class defines the interface that all AI CLI adapters must implement.
    It supports two output acquisition modes:
    1. File watching mode - for CLIs that output to log files (e.g., Claude Code)
    2. Stdout reading mode - for CLIs that output directly to stdout (e.g., OpenCode)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the adapter with configuration.

        Args:
            config: Configuration dictionary for the adapter
        """
        self.config = config

    @abstractmethod
    def get_command(self, project_path: str, **kwargs) -> List[str]:
        """
        Generate the command to start the AI CLI process.

        Args:
            project_path: Path to the project directory
            **kwargs: Additional command-line arguments

        Returns:
            List of command components (binary and arguments)
        """
        pass

    @abstractmethod
    def needs_file_watcher(self) -> bool:
        """
        Indicate whether this adapter requires file watching.

        Returns:
            True if file watching is needed, False if stdout reading is sufficient
        """
        pass

    @abstractmethod
    def get_log_file_path(self, project_path: str) -> Optional[str]:
        """
        Get the path to the log file for file watching mode.

        Args:
            project_path: Path to the project directory

        Returns:
            Path to the log file, or None if file watching is not needed
        """
        pass

    @abstractmethod
    def parse_output(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single line of output from the AI CLI.

        Args:
            line: A single line of output (from file or stdout)

        Returns:
            Parsed output as a dictionary, or None if parsing fails
        """
        pass

    @abstractmethod
    def format_input(self, message: str) -> str:
        """
        Format user input for the AI CLI.

        Args:
            message: User message to send

        Returns:
            Formatted message ready to be sent to stdin
        """
        pass

    @abstractmethod
    async def get_output_stream(self, process: asyncio.subprocess.Process) -> AsyncIterator[str]:
        """
        Get an async iterator for reading output from the process.

        For file watching mode: This may return an empty iterator
        For stdout reading mode: This yields lines from stdout

        Args:
            process: The subprocess instance

        Yields:
            Lines of output from the process
        """
        pass

    def get_name(self) -> str:
        """
        Get the human-readable name of this adapter.

        Returns:
            Name of the AI CLI
        """
        return self.__class__.__name__.replace("Adapter", "")

    def get_version(self) -> Optional[str]:
        """
        Get the version of this adapter.

        Returns:
            Version string, or None if not available
        """
        return None

    def get_description(self) -> Optional[str]:
        """
        Get a description of this AI CLI.

        Returns:
            Description string, or None if not available
        """
        return None

    def validate_config(self) -> bool:
        """
        Validate the adapter configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        return True

    def get_env_vars(self) -> Dict[str, str]:
        """
        Get environment variables to set for the AI CLI process.

        Returns:
            Dictionary of environment variables
        """
        env_vars = {}

        # Add API key if present
        if "api_key" in self.config and self.config["api_key"]:
            # Adapter subclasses can override to use appropriate env var name
            pass

        return env_vars
