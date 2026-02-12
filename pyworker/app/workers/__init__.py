"""Workers - Worker implementations"""

from .v1.claude import ClaudeCodeWorker
from .v1.opencode import OpenCodeWorker

# 映射表
handlers = {
    "claudecode": ClaudeCodeWorker,
    "opencode": OpenCodeWorker,
}

default = "claudecode"
