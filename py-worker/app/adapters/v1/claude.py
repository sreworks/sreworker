"""Claude Code adapter implementation."""

import json
import os
from typing import List, Optional, Dict, Any, AsyncIterator
import asyncio
from .base import BaseWorkerAdapter


class ClaudeAdapter(BaseWorkerAdapter):
    """
    Adapter for Claude Code CLI.

    Claude Code outputs to a project.jsonl file, so this adapter uses file watching mode.
    """

    def get_command(self, project_path: str, **kwargs) -> List[str]:
        """
        Generate command to start Claude Code.

        Args:
            project_path: Path to the project directory
            **kwargs: Additional command-line arguments

        Returns:
            Command components list
        """
        binary = self.config.get("binary", "claude")
        cmd = [binary, "--project", project_path]

        # Add model if specified
        if "model" in self.config and self.config["model"]:
            cmd.extend(["--model", self.config["model"]])

        return cmd

    def needs_file_watcher(self) -> bool:
        """Claude Code requires file watching."""
        return True

    def get_log_file_path(self, project_path: str) -> Optional[str]:
        """
        Get the path to the project.jsonl log file.

        Args:
            project_path: Path to the project directory

        Returns:
            Path to the project.jsonl file
        """
        return os.path.join(project_path, ".claude", "project.jsonl")

    def parse_output(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a line from project.jsonl file.

        Args:
            line: A single line from the JSONL file

        Returns:
            Parsed JSON object, or None if parsing fails
        """
        try:
            line = line.strip()
            if not line:
                return None

            data = json.loads(line)
            return data
        except json.JSONDecodeError as e:
            # Log error but don't crash
            print(f"Failed to parse Claude output: {e}")
            return None

    def format_input(self, message: str) -> str:
        """
        Format user input for Claude Code.

        Args:
            message: User message to send

        Returns:
            Formatted message (just the message as-is for Claude Code)
        """
        return message + "\n"

    async def get_output_stream(self, process: asyncio.subprocess.Process) -> AsyncIterator[str]:
        """
        Get output stream for Claude Code.

        Since Claude Code uses file watching, this returns an empty iterator.
        The file watcher service will handle reading the output.

        Args:
            process: The subprocess instance

        Yields:
            Nothing (empty iterator)
        """
        # For file watching mode, we don't read from stdout
        # The file watcher service will handle reading the log file
        return
        yield  # Make this a generator function

    def get_name(self) -> str:
        """Get adapter name."""
        return "Claude Code"

    def get_description(self) -> Optional[str]:
        """Get adapter description."""
        return "Anthropic's official AI programming assistant"

    def get_env_vars(self) -> Dict[str, str]:
        """
        Get environment variables for Claude Code.

        Returns:
            Dictionary with ANTHROPIC_API_KEY if configured
        """
        env_vars = {}

        # If api_key is provided in config, use it
        if "api_key" in self.config and self.config["api_key"]:
            env_vars["ANTHROPIC_API_KEY"] = self.config["api_key"]
        # Otherwise, if system environment has ANTHROPIC_API_KEY, don't override it
        # (the environment will be inherited by the subprocess)

        return env_vars

    def validate_config(self) -> bool:
        """
        Validate Claude adapter configuration.

        Returns:
            True if configuration is valid
        """
        # Check if API key is provided in config
        if self.config.get("api_key"):
            print("✅ Using ANTHROPIC_API_KEY from .env configuration")
            return True

        # Check if API key is available in system environment
        if os.environ.get("ANTHROPIC_API_KEY"):
            print("✅ Using ANTHROPIC_API_KEY from system environment")
            return True

        # No API key found - but Claude Code might be authenticated via `claude login`
        print("⚠️  Warning: No ANTHROPIC_API_KEY found in config or environment")
        print("   Attempting to use Claude Code's built-in authentication")
        print("   If Claude Code is logged in via 'claude login', this should work")
        print("   Otherwise, please set ANTHROPIC_API_KEY in .env or environment")

        # Return True to allow startup - let Claude Code handle authentication
        return True
