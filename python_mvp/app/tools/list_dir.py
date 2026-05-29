from __future__ import annotations

from typing import Any

from app.permissions import ToolCapability
from app.tool_registry import ToolContext, ToolResult
from app.tools.path_guard import WorkspacePathError, resolve_workspace_path


class ListDirTool:
    name = "list_dir"
    description = "List files and directories inside the workspace."
    capability = ToolCapability.READ

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
        if not path.is_dir():
            return ToolResult(ok=False, content=f"not a directory: {raw_path}")

        names = []
        for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
            suffix = "/" if child.is_dir() else ""
            names.append(f"{child.name}{suffix}")
        return ToolResult(ok=True, content="\n".join(names))
