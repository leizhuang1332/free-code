from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4


Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class Message:
    role: Role
    content: str
    id: str = field(default_factory=lambda: str(uuid4()))
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_uses: list[ToolUse] = field(default_factory=list)
    is_error: bool = False


@dataclass
class AssistantTurn:
    text: str
    tool_uses: list[ToolUse] = field(default_factory=list)

    def to_message(self) -> Message:
        return Message(
            role="assistant",
            content=self.text,
            tool_uses=list(self.tool_uses),
        )


@dataclass
class AssistantEvent:
    text: str


@dataclass
class ToolUseEvent:
    name: str
    input: dict[str, Any]


@dataclass
class ToolResultEvent:
    name: str
    ok: bool
    preview: str


@dataclass
class ErrorEvent:
    message: str


QueryEvent = AssistantEvent | ToolUseEvent | ToolResultEvent | ErrorEvent
