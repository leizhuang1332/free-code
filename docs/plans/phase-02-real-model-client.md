# Phase 2 DeepSeek Model Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留 `FakeModelClient` 测试基线的前提下，接入 DeepSeek 的 OpenAI-compatible API，并把 provider 的消息、工具 schema、tool call 格式隔离在 `model_client.py` 内。

**Architecture:** 新增 `DeepSeekOpenAIClient` 作为 `ModelClient` 实现，内部使用 OpenAI Python SDK 的 `chat.completions.create`，并固定默认 `base_url=https://api.deepseek.com`、`model=deepseek-v4-flash`。本 phase 不改变 `query_loop` 的接口，也不引入 REPL。

**Tech Stack:** Python 3.11+、uv、OpenAI Python SDK、DeepSeek OpenAI-compatible API、pytest、monkeypatch。

---

## 文件结构

- Modify: `python_mvp/pyproject.toml` 和 `python_mvp/uv.lock`，通过 uv 增加 `openai` SDK 依赖。
- Modify: `python_mvp/app/model_client.py`，增加 DeepSeek client 和 OpenAI-compatible chat 格式转换函数。
- Create: `python_mvp/tests/test_model_client.py`，用 fake SDK object 测试转换逻辑，不访问网络。

## Task 1: 增加 SDK 依赖和配置约定

**Files:**
- Modify: `python_mvp/pyproject.toml`
- Modify: `python_mvp/uv.lock`

- [ ] **Step 1: 用 uv 添加 OpenAI SDK**

Run: `cd python_mvp && uv add openai`

Expected: `pyproject.toml` 的 `dependencies` 增加 `openai`，`uv.lock` 同步更新。

- [ ] **Step 2: 同步依赖**

Run: `cd python_mvp && uv sync --dev`

Expected: 安装成功，`openai` 可 import。

- [ ] **Step 3: 验证现有测试仍通过**

Run: `cd python_mvp && uv run pytest -q`

Expected: PASS。

- [ ] **Step 4: Commit**

```bash
git add python_mvp/pyproject.toml python_mvp/uv.lock
git commit -m "chore: add openai sdk dependency for deepseek"
```

## Task 2: 内部消息转 Chat Completions 输入

**Files:**
- Modify: `python_mvp/app/model_client.py`
- Create: `python_mvp/tests/test_model_client.py`

- [ ] **Step 1: 写失败测试，覆盖 user/assistant/tool message 转换**

`python_mvp/tests/test_model_client.py` 内容：

```python
from app.messages import Message, ToolUse
from app.model_client import messages_to_chat_messages, tool_schemas_to_chat_tools


def test_messages_to_chat_messages_converts_roles_and_tool_results():
    messages = [
        Message(role="user", content="read README.md"),
        Message(
            role="assistant",
            content="",
            tool_uses=[ToolUse(id="call_1", name="read_file", input={"path": "README.md"})],
        ),
        Message(
            role="tool",
            content="file contents",
            tool_call_id="call_1",
            tool_name="read_file",
        ),
    ]

    converted = messages_to_chat_messages(messages)

    assert converted[0] == {"role": "user", "content": "read README.md"}
    assert converted[1]["role"] == "assistant"
    assert converted[1]["content"] == ""
    assert converted[1]["tool_calls"][0]["id"] == "call_1"
    assert converted[1]["tool_calls"][0]["function"]["name"] == "read_file"
    assert converted[2] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "file contents",
    }


def test_tool_schemas_to_chat_tools_converts_input_schema_to_parameters():
    schemas = [
        {
            "name": "read_file",
            "description": "Read a file.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }
    ]

    converted = tool_schemas_to_chat_tools(schemas)

    assert converted == [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file.",
                "parameters": schemas[0]["input_schema"],
            },
        }
    ]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_model_client.py -q`

Expected: FAIL，提示 `messages_to_chat_messages` 或 `tool_schemas_to_chat_tools` 不存在。

- [ ] **Step 3: 实现转换函数**

在 `python_mvp/app/model_client.py` 追加：

```python
import json
import os
from typing import Any


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"


def messages_to_chat_messages(messages: list[Message]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for message in messages:
        if message.role in {"user", "assistant"}:
            item: dict[str, Any] = {"role": message.role, "content": message.content}
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
```

- [ ] **Step 4: 运行测试**

Run: `cd python_mvp && uv run pytest tests/test_model_client.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/model_client.py python_mvp/tests/test_model_client.py
git commit -m "feat: convert mvp messages to chat completions format"
```

## Task 3: Chat Completions 输出转 AssistantTurn

**Files:**
- Modify: `python_mvp/app/model_client.py`
- Modify: `python_mvp/tests/test_model_client.py`

- [ ] **Step 1: 写失败测试，覆盖文本和函数调用解析**

追加到 `python_mvp/tests/test_model_client.py`：

```python
from app.model_client import chat_message_to_assistant_turn


def test_chat_message_to_assistant_turn_parses_text_and_tool_calls():
    message = {
        "content": "Need a file.",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": '{"path": "README.md"}',
                },
            }
        ],
    }

    turn = chat_message_to_assistant_turn(message)

    assert turn.text == "Need a file."
    assert turn.tool_uses[0].id == "call_1"
    assert turn.tool_uses[0].name == "read_file"
    assert turn.tool_uses[0].input == {"path": "README.md"}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_model_client.py -q`

Expected: FAIL，提示函数不存在。

- [ ] **Step 3: 实现输出解析**

在 `python_mvp/app/model_client.py` 追加：

```python
def _get_value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def chat_message_to_assistant_turn(message: Any) -> AssistantTurn:
    text = _get_value(message, "content") or ""
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

    return AssistantTurn(text=text, tool_uses=tool_uses)
```

同时确保 `model_client.py` import：

```python
from app.messages import AssistantTurn, Message, ToolUse
```

- [ ] **Step 4: 运行测试**

Run: `cd python_mvp && uv run pytest tests/test_model_client.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/model_client.py python_mvp/tests/test_model_client.py
git commit -m "feat: parse chat completions output"
```

## Task 4: 实现 DeepSeekOpenAIClient

**Files:**
- Modify: `python_mvp/app/model_client.py`
- Modify: `python_mvp/tests/test_model_client.py`

- [ ] **Step 1: 写失败测试，使用 fake SDK client 验证 complete 参数**

追加：

```python
from app.model_client import DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DeepSeekOpenAIClient


class FakeChatCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = type("FakeMessage", (), {"content": "ok", "tool_calls": []})()
        choice = type("FakeChoice", (), {"message": message})()
        return type("FakeResponse", (), {"choices": [choice]})()


class FakeChat:
    def __init__(self):
        self.completions = FakeChatCompletions()


class FakeOpenAI:
    def __init__(self):
        self.chat = FakeChat()


def test_deepseek_client_calls_chat_completions_with_model_messages_and_tools():
    sdk = FakeOpenAI()
    client = DeepSeekOpenAIClient(client=sdk, model="deepseek-test")

    turn = client.complete(
        system_prompt="You are helpful.",
        messages=[Message(role="user", content="hi")],
        tools=[{"name": "echo", "description": "Echo", "input_schema": {"type": "object"}}],
    )

    assert turn.text == "ok"
    assert sdk.chat.completions.kwargs["model"] == "deepseek-test"
    assert sdk.chat.completions.kwargs["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "hi"},
    ]
    assert sdk.chat.completions.kwargs["tools"][0]["function"]["name"] == "echo"


def test_deepseek_client_from_env_uses_deepseek_defaults(monkeypatch):
    captured = {}

    class CapturingOpenAI:
        def __init__(self, api_key, base_url):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            self.chat = FakeChat()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "key")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)

    client = DeepSeekOpenAIClient.from_env(openai_factory=CapturingOpenAI)

    assert client.model == DEEPSEEK_MODEL
    assert captured == {"api_key": "key", "base_url": DEEPSEEK_BASE_URL}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_model_client.py -q`

Expected: FAIL，提示 `DeepSeekOpenAIClient` 不存在。

- [ ] **Step 3: 实现 client**

在 `python_mvp/app/model_client.py` 追加：

```python
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
```

- [ ] **Step 4: 运行测试**

Run: `cd python_mvp && uv run pytest tests/test_model_client.py -q`

Expected: PASS。

- [ ] **Step 5: 全量测试**

Run: `cd python_mvp && uv run pytest -q`

Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add python_mvp/app/model_client.py python_mvp/tests/test_model_client.py
git commit -m "feat: add deepseek openai-compatible model client"
```

## Phase 验收

- [ ] `FakeModelClient` 测试仍然通过。
- [ ] `DeepSeekOpenAIClient.complete()` 不把 provider 格式泄漏到 `query_loop`。
- [ ] 默认 `base_url` 是 `https://api.deepseek.com`。
- [ ] 默认模型是 `deepseek-v4-flash`。
- [ ] provider 输出中的文本和 function call 都能转换为 `AssistantTurn`。
- [ ] 没有配置 `DEEPSEEK_API_KEY` 时，单元测试仍不访问网络。
