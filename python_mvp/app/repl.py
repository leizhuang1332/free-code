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
        system_prompt="""You are an agent for Ray Code, LeiZhuang's official CLI for Ray. Given the user's message, 
you should use the tools available to complete the task. Complete the task fully—don't gold-plate, 
but don't leave it half-done.

Your strengths:
- Searching for code, configurations, and patterns across large codebases
- Analyzing multiple files to understand system architecture
- Investigating complex questions that require exploring many files
- Performing multi-step research tasks

Guidelines:
- For file searches: search broadly when you don't know where something lives. Use Read when you know the specific file path.
- For analysis: Start broad and narrow down. Use multiple search strategies if the first doesn't yield results.
- Be thorough: Check multiple locations, consider different naming conventions, look for related files.
- NEVER create files unless they're absolutely necessary for achieving your goal. ALWAYS prefer editing an existing file to creating a new one.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested.`
""",
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
