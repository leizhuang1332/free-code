from __future__ import annotations

from collections.abc import Iterator

from app.messages import AssistantEvent, ErrorEvent, Message, QueryEvent, ToolResultEvent
from app.model_client import ModelClient
from app.tool_runner import ToolRunner


def query_loop(
    messages: list[Message],
    system_prompt: str,
    model_client: ModelClient,
    tool_runner: ToolRunner,
    max_turns: int = 8,
) -> Iterator[QueryEvent]:
    for _turn in range(max_turns):
        try:
            assistant = model_client.complete(
                system_prompt=system_prompt,
                messages=messages,
                tools=tool_runner.tool_schemas(),
            )
        except Exception as exc:
            yield ErrorEvent(message=f"model failed: {exc}")
            return

        assistant_message = assistant.to_message()
        messages.append(assistant_message)
        yield AssistantEvent(text=assistant.text)

        if not assistant.tool_uses:
            return

        for result_message in tool_runner.run_all(assistant.tool_uses):
            messages.append(result_message)
            yield ToolResultEvent(
                name=result_message.tool_name or "unknown",
                ok=not result_message.is_error,
                preview=result_message.content[:200],
            )

    yield ErrorEvent(message="max_turns reached")
