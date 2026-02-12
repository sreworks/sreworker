"""Claude Code Worker 实现"""

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Any

from .base import BaseWorker
from ...utils.logger import get_app_logger


class ClaudeCodeWorker(BaseWorker):
    """Claude Code CLI Worker 实现"""

    # Claude Code stores sessions in ~/.claude/projects/
    CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

    def __init__(self, env_vars: Optional[Dict[str, str]] = None, command_params: Optional[List[str]] = None):
        self.env_vars = env_vars or {}
        self.command_params = command_params or []
        self.logger = get_app_logger()

    async def start_conversation(self, path: str, message: str) -> str:
        """
        启动新会话

        Args:
            path: 工作目录路径
            message: 初始消息

        Returns:
            raw_conversation_id: Claude Code 会话 ID (session_id)
        """
        # 检查 project_path 是否存在
        if not Path(path).exists():
            raise RuntimeError(f"project_path does not exist: {path}")

        # 检查 claude 命令是否存在
        if shutil.which("claude") is None:
            raise RuntimeError("claude command not found in PATH")

        cmd = ["claude", "--print", "--output-format", "json"]
        cmd.append(message)
        cmd.extend(self.command_params)

        self.logger.info(f"[ClaudeCode] start_conversation: cwd={path}, cmd={' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=path,
            env={**os.environ, **self.env_vars}
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            self.logger.error(f"[ClaudeCode] start_conversation failed: {stderr.decode()}")
            raise RuntimeError(f"Claude Code failed: {stderr.decode()}")

        # 解析 JSON 输出，提取 session_id
        result = json.loads(stdout.decode())
        raw_conversation_id = result.get("session_id", "")

        if not raw_conversation_id:
            raise RuntimeError("No session_id in Claude Code response")

        self.logger.info(f"[ClaudeCode] start_conversation success: session_id={raw_conversation_id}")
        return raw_conversation_id

    async def achieve_conversation(self, raw_conversation_id: str) -> bool:
        """
        归档会话

        Returns:
            是否成功
        """
        # Claude Code 会话自动保存，无需显式归档
        return True

    async def continue_conversation(self, raw_conversation_id: str, path: str, message: str) -> bool:
        """
        继续已有会话

        Args:
            raw_conversation_id: 会话 ID
            path: 工作目录路径
            message: 消息内容

        Returns:
            是否成功
        """
        cmd = ["claude", "--print", "--output-format", "json", "--resume", raw_conversation_id]
        cmd.append(message)
        cmd.extend(self.command_params)

        self.logger.info(f"[ClaudeCode] continue_conversation: cwd={path}, cmd={' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=path,
            env={**os.environ, **self.env_vars}
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            self.logger.error(f"[ClaudeCode] continue_conversation failed: {stderr.decode()}")
            raise RuntimeError(f"Claude Code failed: {stderr.decode()}")

        self.logger.info(f"[ClaudeCode] continue_conversation success: session_id={raw_conversation_id}")
        return True

    def _find_session_file(self, session_id: str) -> Optional[Path]:
        """
        查找 Claude Code 会话文件

        Args:
            session_id: 会话 ID

        Returns:
            会话文件路径，未找到返回 None
        """
        if not self.CLAUDE_PROJECTS_DIR.exists():
            return None

        # Search in all project directories
        for project_dir in self.CLAUDE_PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                session_file = project_dir / f"{session_id}.jsonl"
                if session_file.exists():
                    return session_file

        return None

    async def sync_messages(self, raw_conversation_id: str) -> List[Dict[str, Any]]:
        """
        从 Claude Code 同步会话消息

        Args:
            raw_conversation_id: Claude Code session_id

        Returns:
            原始消息列表（Claude Code JSONL 格式）
        """
        session_file = self._find_session_file(raw_conversation_id)
        if not session_file:
            return []

        messages = []
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line.strip())
                        messages.append(data)
                    except json.JSONDecodeError:
                        continue

        return messages
