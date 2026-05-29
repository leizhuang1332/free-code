from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.permissions import ToolCapability
from app.tool_registry import ToolContext, ToolResult
from app.tools.path_guard import WorkspacePathError, resolve_workspace_path


class GrepTool:
    name = "grep"
    description = (
        "Search for patterns in files using regular expressions or fixed strings. "
        "Returns matching lines with line numbers. "
        "Skips binary files and hidden files/directories by default."
    )
    capability = ToolCapability.READ

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The search pattern (regex by default; use fixed_string=true for plain text).",
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory path to search in.",
                    },
                    "fixed_string": {
                        "type": "boolean",
                        "description": "Treat pattern as a fixed/literal string instead of a regex.",
                        "default": False,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of matching lines to return (0 for unlimited).",
                        "default": 50,
                    },
                    "case_insensitive": {
                        "type": "boolean",
                        "description": "Perform case-insensitive matching.",
                        "default": False,
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "description": "Include hidden files and directories (those starting with '.').",
                        "default": False,
                    },
                },
                "required": ["pattern", "path"],
            },
        }

    def run(self, input: dict[str, Any], context: ToolContext) -> ToolResult:
        # --- Validate pattern ---
        raw_pattern = input.get("pattern")
        if not isinstance(raw_pattern, str) or not raw_pattern:
            return ToolResult(ok=False, content="pattern must be a non-empty string")

        # --- Validate path ---
        raw_path = input.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            return ToolResult(ok=False, content="path must be a non-empty string")

        try:
            path = resolve_workspace_path(context.workspace, raw_path)
        except WorkspacePathError as exc:
            return ToolResult(ok=False, content=str(exc))

        if not path.exists():
            return ToolResult(ok=False, content=f"path does not exist: {raw_path}")

        # --- Extract optional parameters ---
        fixed_string = bool(input.get("fixed_string", False))
        max_results = int(input.get("max_results", 50))
        case_insensitive = bool(input.get("case_insensitive", False))
        include_hidden = bool(input.get("include_hidden", False))

        if max_results < 0:
            return ToolResult(ok=False, content="max_results must be a non-negative integer")

        # --- Compile regex ---
        try:
            if fixed_string:
                pattern_str = re.escape(raw_pattern)
            else:
                pattern_str = raw_pattern

            flags = re.MULTILINE
            if case_insensitive:
                flags |= re.IGNORECASE

            compiled = re.compile(pattern_str, flags)
        except re.error as exc:
            return ToolResult(ok=False, content=f"invalid regex pattern: {exc}")

        # --- Search ---
        results: list[str] = []
        files_searched = 0
        files_with_matches = 0

        if path.is_file():
            files_searched = 1
            file_results = self._search_file(path, compiled)
            if file_results:
                files_with_matches = 1
                for line_info in file_results:
                    results.append(f"{path}:{line_info}")
                    if max_results > 0 and len(results) >= max_results:
                        break
        elif path.is_dir():
            for root_str, dirs, files in os.walk(path):
                root = Path(root_str)

                # Filter hidden directories when walking
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    files = [f for f in files if not f.startswith(".")]

                for file in sorted(files):
                    filepath = root / file
                    files_searched += 1
                    file_results = self._search_file(filepath, compiled)
                    if file_results:
                        files_with_matches += 1
                        for line_info in file_results:
                            results.append(f"{filepath}:{line_info}")
                            if max_results > 0 and len(results) >= max_results:
                                break
                    if max_results > 0 and len(results) >= max_results:
                        break
                if max_results > 0 and len(results) >= max_results:
                    break
        else:
            return ToolResult(ok=False, content=f"not a file or directory: {raw_path}")

        # --- Build output ---
        if not results:
            return ToolResult(
                ok=True,
                content=f"No matches found. Searched {files_searched} file(s).",
            )

        summary = (
            f"Found {len(results)} match(es) in {files_with_matches} file(s) "
            f"(searched {files_searched} file(s))"
        )

        if max_results > 0 and len(results) >= max_results:
            summary += f". Truncated to {max_results} results. Increase max_results for more."

        output = summary + "\n\n" + "\n".join(results)
        return ToolResult(ok=True, content=output)

    # ------------------------------------------------------------------
    def _search_file(self, filepath: Path, compiled: re.Pattern) -> list[str]:
        """Return a list of 'line_number:line_content' for each match."""
        try:
            content = filepath.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            return []  # skip binary or unreadable files

        matches: list[str] = []
        for line_no, line in enumerate(content.splitlines(), 1):
            if compiled.search(line):
                matches.append(f"{line_no}:{line}")
        return matches
