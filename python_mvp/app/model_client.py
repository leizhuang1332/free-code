from __future__ import annotations

import json
import os
from typing import Any, Protocol

from dotenv import load_dotenv

from app.messages import AssistantTurn, Message, ToolUse

load_dotenv()


class ModelClient(Protocol):
    def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tools: list[dict],
    ) -> AssistantTurn:
        ...


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"


def messages_to_chat_messages(messages: list[Message]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for message in messages:
        if message.role in {"user", "assistant"}:
            item: dict[str, Any] = {"role": message.role, "content": message.content}
            if message.role == "assistant" and message.reasoning_content:
                item["reasoning_content"] = message.reasoning_content
            if message.tool_uses:
                item["tool_calls"] = [
                    {
                        "id": tool_use.id,
                        "type": "function",
                        "function": {
                            "name": tool_use.name,
                            "arguments": json.dumps(tool_use.input),
                        },
                    }
                    for tool_use in message.tool_uses
                ]
            converted.append(item)
            continue

        if message.role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": message.tool_call_id or "",
                    "content": message.content,
                }
            )
            continue

        if message.role == "system":
            converted.append({"role": "system", "content": message.content})

    return converted


def tool_schemas_to_chat_tools(schemas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema.get("description", ""),
                "parameters": schema.get("input_schema", {"type": "object"}),
            },
        }
        for schema in schemas
    ]


def _get_value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def chat_message_to_assistant_turn(message: Any) -> AssistantTurn:
    text = _get_value(message, "content") or ""
    reasoning_content = _get_value(message, "reasoning_content", None)
    tool_uses: list[ToolUse] = []

    for call in _get_value(message, "tool_calls", []) or []:
        function = _get_value(call, "function", {})
        raw_arguments = _get_value(function, "arguments", "{}") or "{}"
        try:
            parsed_arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            parsed_arguments = {"_raw": raw_arguments}
        tool_uses.append(
            ToolUse(
                id=_get_value(call, "id", ""),
                name=_get_value(function, "name", ""),
                input=parsed_arguments,
            )
        )

    return AssistantTurn(text=text, tool_uses=tool_uses, reasoning_content=reasoning_content)


class FakeModelClient:
    def __init__(self, turns: list[AssistantTurn]) -> None:
        self._turns = list(turns)
        self.call_count = 0

    def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tools: list[dict],
    ) -> AssistantTurn:
        if self.call_count >= len(self._turns):
            raise RuntimeError("FakeModelClient has no remaining turns")
        turn = self._turns[self.call_count]
        self.call_count += 1
        return turn


class DeepSeekOpenAIClient:
    def __init__(self, client: Any, model: str = DEEPSEEK_MODEL) -> None:
        self._client = client
        self.model = model

    @classmethod
    def from_env(cls, openai_factory: Any | None = None) -> "DeepSeekOpenAIClient":
        from openai import OpenAI

        factory = openai_factory or OpenAI
        api_key = os.environ["DEEPSEEK_API_KEY"]
        base_url = os.environ.get("DEEPSEEK_BASE_URL", DEEPSEEK_BASE_URL)
        model = os.environ.get("DEEPSEEK_MODEL", DEEPSEEK_MODEL)
        return cls(client=factory(api_key=api_key, base_url=base_url), model=model)

    def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tools: list[dict],
    ) -> AssistantTurn:
        chat_messages = [{"role": "system", "content": system_prompt}]
        chat_messages.extend(messages_to_chat_messages(messages))
        response = self._client.chat.completions.create(
            model=self.model,
            messages=chat_messages,
            tools=tool_schemas_to_chat_tools(tools),
        )
        return chat_message_to_assistant_turn(response.choices[0].message)
