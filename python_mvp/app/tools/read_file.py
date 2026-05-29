from __future__ import annotations

from typing import Any

from app.permissions import ToolCapability
from app.tool_registry import ToolContext, ToolResult
from app.tools.path_guard import WorkspacePathError, resolve_workspace_path


class ReadFileTool:
    name = "read_file"
    description = "Read a UTF-8 text file inside the workspace."
    capability = ToolCapability.READ

    def __init__(self, max_bytes: int = 64_000) -> None:
        self._max_bytes = max_bytes

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }

    def run(self, input: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_path = input.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            return ToolResult(ok=False, content="path must be a non-empty string")

        try:
            path = resolve_workspace_path(context.workspace, raw_path)
        except WorkspacePathError as exc:
            return ToolResult(ok=False, content=str(exc))

        if not path.exists():
            return ToolResult(ok=False, content=f"path does not exist: {raw_path}")
        if not path.is_file():
            return ToolResult(ok=False, content=f"not a file: {raw_path}")
        if path.stat().st_size > self._max_bytes:
            return ToolResult(ok=False, content=f"file too large: {raw_path}")

        try:
            return ToolResult(ok=True, content=path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            return ToolResult(ok=False, content=f"file is not valid UTF-8 text: {raw_path}")
