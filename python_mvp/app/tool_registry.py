from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.permissions import ToolCapability


@dataclass
class ToolContext:
    workspace: Path


@dataclass
class ToolResult:
    ok: bool
    content: str


class Tool(Protocol):
    name: str
    description: str
    capability: ToolCapability

    def schema(self) -> dict[str, Any]:
        ...

    def run(self, input: dict[str, Any], context: ToolContext) -> ToolResult:
        ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]
