"""JSONL file parser utility."""

import json
import os
from typing import Optional, List, Dict, Any
import aiofiles


class JSONLParser:
    """Parser for JSONL (JSON Lines) files with incremental reading support."""

    def __init__(self, file_path: str):
        """
        Initialize the JSONL parser.

        Args:
            file_path: Path to the JSONL file
        """
        self.file_path = file_path
        self.last_position = 0

    async def read_new_lines(self) -> List[Dict[str, Any]]:
        """
        Read new lines added since last read.

        Returns:
            List of parsed JSON objects from new lines
        """
        if not os.path.exists(self.file_path):
            return []

        new_data = []

        try:
            async with aiofiles.open(self.file_path, mode='r', encoding='utf-8') as f:
                # Seek to last read position
                await f.seek(self.last_position)

                # Read new lines
                async for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        new_data.append(data)
                    except json.JSONDecodeError as e:
                        # Log error but continue processing
                        print(f"Failed to parse JSONL line: {e}")
                        continue

                # Update last position
                self.last_position = await f.tell()

        except Exception as e:
            print(f"Error reading JSONL file: {e}")

        return new_data

    def reset_position(self) -> None:
        """Reset the read position to the beginning of the file."""
        self.last_position = 0

    async def read_all_lines(self) -> List[Dict[str, Any]]:
        """
        Read all lines from the file.

        Returns:
            List of parsed JSON objects from all lines
        """
        if not os.path.exists(self.file_path):
            return []

        all_data = []

        try:
            async with aiofiles.open(self.file_path, mode='r', encoding='utf-8') as f:
                async for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        all_data.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSONL line: {e}")
                        continue

        except Exception as e:
            print(f"Error reading JSONL file: {e}")

        return all_data

    def get_file_size(self) -> int:
        """
        Get the current size of the file.

        Returns:
            File size in bytes, or 0 if file doesn't exist
        """
        try:
            return os.path.getsize(self.file_path)
        except OSError:
            return 0


def parse_jsonl_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single JSONL line.

    Args:
        line: A single line of JSON

    Returns:
        Parsed JSON object, or None if parsing fails
    """
    try:
        line = line.strip()
        if not line:
            return None

        return json.loads(line)
    except json.JSONDecodeError:
        return None
