"""Workers V1 - Worker implementations"""

from .base import BaseWorker
from .claude import ClaudeCodeWorker
from .opencode import OpenCodeWorker

# 简单的映射表
handlers = {
    "claudecode": ClaudeCodeWorker,
    "claude": ClaudeCodeWorker,
    "opencode": OpenCodeWorker,
}

default = "claudecode"

__all__ = [
    "BaseWorker",
    "ClaudeCodeWorker",
    "OpenCodeWorker",
    "handlers",
    "default",
]
