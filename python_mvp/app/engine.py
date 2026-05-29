from __future__ import annotations

from collections.abc import Iterator

from app.input_processor import process_user_input
from app.messages import AssistantEvent, Message, QueryEvent
from app.model_client import ModelClient
from app.query_loop import query_loop
from app.tool_runner import ToolRunner
from app.transcript import TranscriptStore


class SessionEngine:
    def __init__(
        self,
        model_client: ModelClient,
        tool_runner: ToolRunner,
        transcript: TranscriptStore,
        system_prompt: str,
    ) -> None:
        self._model_client = model_client
        self._tool_runner = tool_runner
        self._transcript = transcript
        self._system_prompt = system_prompt
        self.messages: list[Message] = []

    def submit(self, user_input: str) -> Iterator[QueryEvent]:
        processed = process_user_input(user_input)

        if processed.clear_messages:
            self.messages.clear()

        if processed.local_output is not None:
            yield AssistantEvent(text=processed.local_output)
            return

        for message in processed.messages:
            self.messages.append(message)
            self._transcript.append_message("user", message)

        if not processed.should_query:
            return

        before_count = len(self.messages)
        for event in query_loop(
            messages=self.messages,
            system_prompt=self._system_prompt,
            model_client=self._model_client,
            tool_runner=self._tool_runner,
        ):
            self._write_new_messages(before_count)
            before_count = len(self.messages)
            yield event

    def _write_new_messages(self, start_index: int) -> None:
        for message in self.messages[start_index:]:
            if message.role == "assistant":
                self._transcript.append_message("assistant", message)
            elif message.role == "tool":
                self._transcript.append_message("tool_result", message)
