from __future__ import annotations

import subprocess
import sys
from typing import Any

from app.permissions import ToolCapability
from app.tool_registry import ToolContext, ToolResult


class BashTool:
    name = "bash"
    description = "Execute a bash command in the workspace."
    capability = ToolCapability.EXECUTE

    def __init__(self, default_timeout: int = 30) -> None:
        self._default_timeout = default_timeout

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Optional timeout in seconds (default 30).",
                        "default": self._default_timeout,
                    },
                },
                "required": ["command"],
            },
        }

    def run(self, input: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_command = input.get("command")
        if not isinstance(raw_command, str) or not raw_command.strip():
            return ToolResult(ok=False, content="command must be a non-empty string")

        timeout = self._default_timeout
        raw_timeout = input.get("timeout")
        if raw_timeout is not None:
            if not isinstance(raw_timeout, (int, float)) or raw_timeout <= 0:
                return ToolResult(ok=False, content="timeout must be a positive number")
            timeout = int(raw_timeout)

        try:
            result = subprocess.run(
                raw_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(context.workspace),
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                ok=False,
                content=f"command timed out after {timeout}s: {raw_command[:200]}",
            )
        except OSError as exc:
            return ToolResult(ok=False, content=f"failed to execute command: {exc}")

        merged = self._merge_output(result)
        return ToolResult(ok=(result.returncode == 0), content=merged)

    def _merge_output(self, result: subprocess.CompletedProcess) -> str:
        parts = []
        if result.stdout:
            parts.append(result.stdout.rstrip("\n"))
        if result.stderr:
            label = "stderr:" if result.stdout else ""
            parts.append(f"{label}{result.stderr.rstrip('\n')}")

        merged = "\n".join(parts)

        if result.returncode != 0:
            prefix = f"exit code {result.returncode}"
            if merged:
                merged = f"{prefix}\n{merged}"
            else:
                merged = prefix

        return merged
