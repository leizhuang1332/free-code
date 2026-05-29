from __future__ import annotations

from typing import Any

from app.permissions import ToolCapability
from app.tool_registry import ToolContext, ToolResult
from app.tools.path_guard import WorkspacePathError, resolve_workspace_path


class EditFileTool:
    name = "edit_file"
    description = (
        "Edit a UTF-8 text file inside the workspace by finding an exact block of text "
        "(old_string) and replacing it with new text (new_string). "
        "The old_string must appear exactly once in the file; otherwise the operation "
        "will be rejected to avoid ambiguity. "
        "Use this tool for targeted edits instead of re-writing the entire file."
    )
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
                    "path": {
                        "type": "string",
                        "description": "The path to the file to edit (relative to workspace or absolute).",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "The exact existing text block to search for. Must match exactly and appear exactly once in the file.",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The new text to replace the old_string with.",
                    },
                },
                "required": ["path", "old_string", "new_string"],
            },
        }

    def run(self, input: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_path = input.get("path")
        old_string = input.get("old_string")
        new_string = input.get("new_string")

        # --- Validate inputs ---
        if not isinstance(raw_path, str) or not raw_path:
            return ToolResult(ok=False, content="path must be a non-empty string")
        if not isinstance(old_string, str) or not old_string:
            return ToolResult(ok=False, content="old_string must be a non-empty string")
        if not isinstance(new_string, str):
            return ToolResult(ok=False, content="new_string must be a string")

        # --- Resolve path ---
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

        # --- Read existing content ---
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ToolResult(ok=False, content=f"file is not valid UTF-8 text: {raw_path}")
        except OSError as exc:
            return ToolResult(ok=False, content=f"failed to read file: {exc}")

        # --- Count occurrences of old_string ---
        occurrences = content.count(old_string)
        if occurrences == 0:
            return ToolResult(
                ok=False,
                content=(
                    f"old_string was not found in {raw_path}. "
                    "Make sure the string matches exactly, including whitespace and indentation."
                ),
            )
        if occurrences > 1:
            return ToolResult(
                ok=False,
                content=(
                    f"old_string appears {occurrences} times in {raw_path}. "
                    "To avoid ambiguity, it must appear exactly once. "
                    "Please provide a more specific block of text."
                ),
            )

        # --- Perform the replacement ---
        new_content = content.replace(old_string, new_string, 1)

        # --- Validate the result isn't too large ---
        if len(new_content.encode("utf-8")) > self._max_bytes:
            return ToolResult(ok=False, content=f"resulting file too large: {raw_path}")

        # --- Write back ---
        try:
            path.write_text(new_content, encoding="utf-8")
        except OSError as exc:
            return ToolResult(ok=False, content=f"failed to write file: {exc}")

        return ToolResult(
            ok=True,
            content=f"Successfully edited {raw_path}. Applied single replacement.",
        )
