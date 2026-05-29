from __future__ import annotations

from dataclasses import dataclass, field

from app.messages import Message


@dataclass
class ProcessedInput:
    messages: list[Message] = field(default_factory=list)
    should_query: bool = True
    local_output: str | None = None
    clear_messages: bool = False


def process_user_input(text: str) -> ProcessedInput:
    normalized = text.strip()
    if normalized == "/help":
        return ProcessedInput(
            should_query=False,
            local_output="Commands: /help, /clear, /exit",
        )
    if normalized == "/clear":
        return ProcessedInput(
            should_query=False,
            local_output="Conversation cleared.",
            clear_messages=True,
        )
    return ProcessedInput(messages=[Message(role="user", content=text)], should_query=True)
