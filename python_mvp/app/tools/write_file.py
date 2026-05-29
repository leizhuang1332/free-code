from __future__ import annotations

from typing import Any

from app.permissions import ToolCapability
from app.tool_registry import ToolContext, ToolResult
from app.tools.path_guard import WorkspacePathError, resolve_workspace_path


class WriteFileTool:
    name = "write_file"
    description = "Write UTF-8 text to a file inside the workspace."
    capability = ToolCapability.WRITE

    def __init__(self, max_bytes: int = 64_000) -> None:
        self._max_bytes = max_bytes

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        }

    def run(self, input: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_path = input.get("path")
        content = input.get("content")
        if not isinstance(raw_path, str) or not raw_path:
            return ToolResult(ok=False, content="path must be a non-empty string")
        if not isinstance(content, str):
            return ToolResult(ok=False, content="content must be a string")
        if len(content.encode("utf-8")) > self._max_bytes:
            return ToolResult(ok=False, content=f"content too large: {raw_path}")

        try:
            path = resolve_workspace_path(context.workspace, raw_path)
        except WorkspacePathError as exc:
            return ToolResult(ok=False, content=str(exc))

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(ok=True, content=f"wrote {raw_path}")
