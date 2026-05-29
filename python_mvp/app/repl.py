from __future__ import annotations

from pathlib import Path

from app.engine import SessionEngine
from app.messages import AssistantEvent, ErrorEvent, ToolResultEvent
from app.model_client import DeepSeekOpenAIClient
from app.permissions import PermissionMode, PermissionPolicy
from app.tool_runner import ToolRunner
from app.tools import create_read_only_registry, create_all_tools_registry
from app.transcript import TranscriptStore


def render_event(event) -> str:
    if isinstance(event, AssistantEvent):
        return event.text
    if isinstance(event, ToolResultEvent):
        status = "ok" if event.ok else "error"
        return f"[tool:{event.name}:{status}] {event.preview}"
    if isinstance(event, ErrorEvent):
        return f"[error] {event.message}"
    return str(event)


def build_engine() -> SessionEngine:
    workspace = Path.cwd()
    registry = create_all_tools_registry()
    return SessionEngine(
        model_client=DeepSeekOpenAIClient.from_env(),
        tool_runner=ToolRunner(
            registry=registry,
            workspace=workspace,
            permission_policy=PermissionPolicy(PermissionMode.ALLOW_ALL),
        ),
        transcript=TranscriptStore(workspace / ".mvp-session.jsonl"),
        system_prompt="You are a coding assistant. Use tools when needed.",
    )


def main() -> None:
    engine = build_engine()
    while True:
        try:
            text = input("> ")
        except EOFError:
            break

        if text.strip() in {"/exit", "exit", "quit"}:
            break

        for event in engine.submit(user_input=text):
            rendered = render_event(event)
            if rendered:
                print(rendered)


if __name__ == "__main__":
    main()
