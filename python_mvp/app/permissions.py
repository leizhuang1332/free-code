from __future__ import annotations

from enum import Enum


class PermissionMode(Enum):
    ALLOW_ALL = "allow_all"
    READ_ONLY = "read_only"
    DENY_ALL = "deny_all"


class ToolCapability(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


class PermissionPolicy:
    def __init__(self, mode: PermissionMode) -> None:
        self.mode = mode

    def can_use_tool(self, tool_name: str, capability: ToolCapability) -> bool:
        if self.mode == PermissionMode.ALLOW_ALL:
            return True
        if self.mode == PermissionMode.DENY_ALL:
            return False
        if self.mode == PermissionMode.READ_ONLY:
            return capability == ToolCapability.READ
        return False
