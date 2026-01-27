"""OpenCode adapter implementation."""

import json
import os
from typing import List, Optional, Dict, Any, AsyncIterator
import asyncio
from .base import BaseWorkerAdapter


class OpenCodeAdapter(BaseWorkerAdapter):
    """
    Adapter for OpenCode CLI.

    OpenCode outputs directly to stdout, so this adapter uses stdout reading mode.
    """

    def get_command(self, project_path: str, **kwargs) -> List[str]:
        """
        Generate command to start OpenCode.

        Args:
            project_path: Path to the project directory
            **kwargs: Additional command-line arguments

        Returns:
            Command components list
        """
        binary = self.config.get("binary", "opencode")
        cmd = [binary, "--workspace", project_path]

        # Add model if specified
        if "model" in self.config and self.config["model"]:
            cmd.extend(["--model", self.config["model"]])

        # Add API base URL if specified
        if "api_base" in self.config and self.config["api_base"]:
            cmd.extend(["--api-base", self.config["api_base"]])

        return cmd

    def needs_file_watcher(self) -> bool:
        """OpenCode does not require file watching."""
        return False

    def get_log_file_path(self, project_path: str) -> Optional[str]:
        """
        OpenCode uses stdout, so no log file is needed.

        Args:
            project_path: Path to the project directory

        Returns:
            None (no log file)
        """
        return None

    def parse_output(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a line from OpenCode stdout.

        Args:
            line: A single line from stdout

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
            print(f"Failed to parse OpenCode output: {e}")
            return None

    def format_input(self, message: str) -> str:
        """
        Format user input for OpenCode.

        Args:
            message: User message to send

        Returns:
            Formatted message (just the message as-is for OpenCode)
        """
        return message + "\n"

    async def get_output_stream(self, process: asyncio.subprocess.Process) -> AsyncIterator[str]:
        """
        Get output stream from OpenCode stdout.

        Args:
            process: The subprocess instance

        Yields:
            Lines from stdout
        """
        if process.stdout is None:
            return

        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                try:
                    decoded_line = line.decode("utf-8")
                    yield decoded_line
                except UnicodeDecodeError:
                    # Skip lines that can't be decoded
                    continue
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            pass

    def get_name(self) -> str:
        """Get adapter name."""
        return "OpenCode"

    def get_description(self) -> Optional[str]:
        """Get adapter description."""
        return "Open source AI programming tool"

    def get_env_vars(self) -> Dict[str, str]:
        """
        Get environment variables for OpenCode.

        Returns:
            Dictionary with OPENCODE_API_KEY if configured
        """
        env_vars = {}

        # If api_key is provided in config, use it
        if "api_key" in self.config and self.config["api_key"]:
            env_vars["OPENCODE_API_KEY"] = self.config["api_key"]
        # Otherwise, if system environment has OPENCODE_API_KEY, don't override it
        # (the environment will be inherited by the subprocess)

        return env_vars

    def validate_config(self) -> bool:
        """
        Validate OpenCode adapter configuration.

        Returns:
            True if configuration is valid
        """
        # Check if API key is provided in config
        if self.config.get("api_key"):
            print("✅ Using OPENCODE_API_KEY from .env configuration")
            return True

        # Check if API key is available in system environment
        if os.environ.get("OPENCODE_API_KEY"):
            print("✅ Using OPENCODE_API_KEY from system environment")
            return True

        # No API key found - but OpenCode might be authenticated via other means
        print("⚠️  Warning: No OPENCODE_API_KEY found in config or environment")
        print("   Attempting to use OpenCode's built-in authentication")
        print("   If OpenCode is configured via other means, this should work")
        print("   Otherwise, please set OPENCODE_API_KEY in .env or environment")

        # Return True to allow startup - let OpenCode handle authentication
        return True
