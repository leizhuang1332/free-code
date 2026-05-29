from __future__ import annotations

from pathlib import Path

from app.messages import Message, ToolUse
from app.permissions import PermissionMode, PermissionPolicy
from app.tool_registry import ToolContext, ToolRegistry


class ToolRunner:
    def __init__(
        self,
        registry: ToolRegistry,
        workspace: Path,
        permission_policy: PermissionPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._context = ToolContext(workspace=workspace)
        self._permission_policy = permission_policy or PermissionPolicy(PermissionMode.ALLOW_ALL)

    def tool_schemas(self) -> list[dict]:
        return self._registry.schemas()

    def run_all(self, tool_uses: list[ToolUse]) -> list[Message]:
        return [self._run_one(tool_use) for tool_use in tool_uses]

    def _run_one(self, tool_use: ToolUse) -> Message:
        tool = self._registry.get(tool_use.name)
        if tool is None:
            return self._tool_message(tool_use, f"unknown tool: {tool_use.name}", is_error=True)

        if not self._permission_policy.can_use_tool(tool.name, tool.capability):
            return self._tool_message(
                tool_use,
                f"permission denied for {tool.name} in {self._permission_policy.mode.name}",
                is_error=True,
            )

        try:
            result = tool.run(tool_use.input, self._context)
        except Exception as exc:
            return self._tool_message(tool_use, f"tool failed: {exc}", is_error=True)

        return self._tool_message(tool_use, result.content, is_error=not result.ok)

    def _tool_message(self, tool_use: ToolUse, content: str, is_error: bool) -> Message:
        return Message(
            role="tool",
            content=content,
            tool_call_id=tool_use.id,
            tool_name=tool_use.name,
            is_error=is_error,
        )
