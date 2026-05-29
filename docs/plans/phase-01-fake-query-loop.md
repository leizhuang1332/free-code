# Phase 1 Fake Query Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 不访问真实模型，用 `FakeModelClient`、`ToolRegistry`、`ToolRunner` 和 `query_loop` 跑通 “assistant tool_use -> tool_result -> assistant final response” 的最小闭环。

**Architecture:** 本 phase 只实现内核对象，不做 REPL、transcript、真实 provider 和文件工具。`query_loop` 负责追加 assistant/tool message，`ToolRunner` 负责串行执行工具，`FakeModelClient` 负责按测试脚本返回预设 assistant turn。

**Tech Stack:** Python 3.11+、uv、dataclasses、typing.Protocol、pytest。

---

## 文件结构

- Create: `python_mvp/pyproject.toml`，定义包元信息和 uv 管理的依赖。
- Create: `python_mvp/app/__init__.py`，包标记。
- Create: `python_mvp/app/messages.py`，定义 `Message`、`ToolUse`、`AssistantTurn`、事件和工具结果结构。
- Create: `python_mvp/app/model_client.py`，定义 `ModelClient` protocol 和 `FakeModelClient`。
- Create: `python_mvp/app/tool_registry.py`，定义工具协议、上下文和注册表。
- Create: `python_mvp/app/tool_runner.py`，执行工具调用并包装 tool result。
- Create: `python_mvp/app/query_loop.py`，实现核心模型循环。
- Create: `python_mvp/tests/test_query_loop.py`，覆盖无工具、有工具、max turns。
- Create: `python_mvp/tests/test_tool_runner.py`，覆盖未知工具和工具异常。

## Task 1: 项目骨架

**Files:**
- Create: `python_mvp/pyproject.toml`
- Create: `python_mvp/app/__init__.py`
- Create: `python_mvp/tests/__init__.py`

- [ ] **Step 1: 创建 Python 包配置**

`python_mvp/pyproject.toml` 内容：

```toml
[project]
name = "python-mvp-session"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: 同步 uv 环境**

Run: `cd python_mvp && uv sync --dev`

Expected: uv 创建或更新 `.venv` 和 `uv.lock`，pytest 可通过 `uv run pytest` 调用。

- [ ] **Step 3: 创建包标记文件**

`python_mvp/app/__init__.py` 内容：

```python
"""Python MVP session execution chain."""
```

`python_mvp/tests/__init__.py` 内容为空文件。

- [ ] **Step 4: 运行空测试套件**

Run: `cd python_mvp && uv run pytest -q`

Expected: pytest 能启动；如果还没有测试，应显示 `no tests ran`。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/pyproject.toml python_mvp/uv.lock python_mvp/app/__init__.py python_mvp/tests/__init__.py
git commit -m "chore: scaffold python mvp package"
```

## Task 2: 消息和事件模型

**Files:**
- Create: `python_mvp/app/messages.py`
- Test: `python_mvp/tests/test_query_loop.py`

- [ ] **Step 1: 写失败测试，验证 assistant turn 可转换为 message**

`python_mvp/tests/test_query_loop.py` 先写入：

```python
from app.messages import AssistantTurn, Message, ToolUse


def test_assistant_turn_converts_to_message_with_tool_use():
    turn = AssistantTurn(
        text="I will call a tool.",
        tool_uses=[ToolUse(id="toolu_1", name="echo", input={"text": "hello"})],
    )

    message = turn.to_message()

    assert isinstance(message, Message)
    assert message.role == "assistant"
    assert message.content == "I will call a tool."
    assert message.tool_uses[0].name == "echo"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_query_loop.py -q`

Expected: FAIL，提示 `No module named 'app.messages'` 或 `AssistantTurn` 未定义。

- [ ] **Step 3: 实现消息模型**

`python_mvp/app/messages.py` 内容：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python_mvp && uv run pytest tests/test_query_loop.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/messages.py python_mvp/tests/test_query_loop.py
git commit -m "feat: add mvp message model"
```

## Task 3: 工具注册表和 echo 工具测试替身

**Files:**
- Create: `python_mvp/app/tool_registry.py`
- Test: `python_mvp/tests/test_tool_runner.py`

- [ ] **Step 1: 写失败测试，验证工具注册和 schema 导出**

`python_mvp/tests/test_tool_runner.py` 初始内容：

```python
from app.tool_registry import ToolContext, ToolRegistry, ToolResult


class EchoTool:
    name = "echo"
    description = "Return the provided text."

    def schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        }

    def run(self, input, context: ToolContext):
        return ToolResult(ok=True, content=input["text"])


def test_tool_registry_registers_and_exports_schemas():
    registry = ToolRegistry()
    tool = EchoTool()

    registry.register(tool)

    assert registry.get("echo") is tool
    assert registry.schemas()[0]["name"] == "echo"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_tool_runner.py -q`

Expected: FAIL，提示 `app.tool_registry` 不存在。

- [ ] **Step 3: 实现工具协议和注册表**

`python_mvp/app/tool_registry.py` 内容：

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python_mvp && uv run pytest tests/test_tool_runner.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/tool_registry.py python_mvp/tests/test_tool_runner.py
git commit -m "feat: add tool registry"
```

## Task 4: ToolRunner 串行执行工具

**Files:**
- Create: `python_mvp/app/tool_runner.py`
- Modify: `python_mvp/tests/test_tool_runner.py`

- [ ] **Step 1: 写失败测试，覆盖成功工具调用、未知工具、工具异常**

追加到 `python_mvp/tests/test_tool_runner.py`：

```python
from pathlib import Path

from app.messages import ToolUse
from app.tool_runner import ToolRunner


class ExplodingTool:
    name = "explode"
    description = "Raise an exception."

    def schema(self):
        return {"name": self.name, "description": self.description, "input_schema": {"type": "object"}}

    def run(self, input, context: ToolContext):
        raise RuntimeError("boom")


def test_tool_runner_wraps_success_as_tool_message():
    registry = ToolRegistry()
    registry.register(EchoTool())
    runner = ToolRunner(registry=registry, workspace=Path.cwd())

    messages = runner.run_all([ToolUse(id="toolu_1", name="echo", input={"text": "hello"})])

    assert messages[0].role == "tool"
    assert messages[0].content == "hello"
    assert messages[0].tool_call_id == "toolu_1"
    assert messages[0].tool_name == "echo"
    assert messages[0].is_error is False


def test_tool_runner_returns_error_for_unknown_tool():
    runner = ToolRunner(registry=ToolRegistry(), workspace=Path.cwd())

    messages = runner.run_all([ToolUse(id="toolu_1", name="missing", input={})])

    assert messages[0].role == "tool"
    assert messages[0].is_error is True
    assert "unknown tool: missing" in messages[0].content


def test_tool_runner_wraps_tool_exception():
    registry = ToolRegistry()
    registry.register(ExplodingTool())
    runner = ToolRunner(registry=registry, workspace=Path.cwd())

    messages = runner.run_all([ToolUse(id="toolu_1", name="explode", input={})])

    assert messages[0].is_error is True
    assert "boom" in messages[0].content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_tool_runner.py -q`

Expected: FAIL，提示 `app.tool_runner` 不存在。

- [ ] **Step 3: 实现 ToolRunner**

`python_mvp/app/tool_runner.py` 内容：

```python
from __future__ import annotations

from pathlib import Path

from app.messages import Message, ToolUse
from app.tool_registry import ToolContext, ToolRegistry


class ToolRunner:
    def __init__(self, registry: ToolRegistry, workspace: Path) -> None:
        self._registry = registry
        self._context = ToolContext(workspace=workspace)

    def tool_schemas(self) -> list[dict]:
        return self._registry.schemas()

    def run_all(self, tool_uses: list[ToolUse]) -> list[Message]:
        return [self._run_one(tool_use) for tool_use in tool_uses]

    def _run_one(self, tool_use: ToolUse) -> Message:
        tool = self._registry.get(tool_use.name)
        if tool is None:
            return self._tool_message(tool_use, f"unknown tool: {tool_use.name}", is_error=True)

        try:
            result = tool.run(tool_use.input, self._context)
        except Exception as exc:
            return self._tool_message(tool_use, f"tool failed: {exc}", is_error=True)

        return self._tool_message(tool_use, result.content, is_error=not result.ok)

    def _tool_message(self, tool_use: ToolUse, content: str, is_error: bool) -> Message:
        return Message(
            role="tool",
            content=content,
            tool_call_id=tool_use.id,
            tool_name=tool_use.name,
            is_error=is_error,
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python_mvp && uv run pytest tests/test_tool_runner.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/tool_runner.py python_mvp/tests/test_tool_runner.py
git commit -m "feat: add serial tool runner"
```

## Task 5: FakeModelClient 和 query_loop

**Files:**
- Create: `python_mvp/app/model_client.py`
- Create: `python_mvp/app/query_loop.py`
- Modify: `python_mvp/tests/test_query_loop.py`

- [ ] **Step 1: 写失败测试，覆盖无工具调用一轮结束**

替换 `python_mvp/tests/test_query_loop.py` 为：

```python
from pathlib import Path

from app.messages import AssistantEvent, AssistantTurn, ErrorEvent, ToolResultEvent, ToolUse
from app.model_client import FakeModelClient
from app.query_loop import query_loop
from app.tool_registry import ToolContext, ToolRegistry, ToolResult
from app.tool_runner import ToolRunner


class EchoTool:
    name = "echo"
    description = "Return the provided text."

    def schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        }

    def run(self, input, context: ToolContext):
        return ToolResult(ok=True, content=input["text"])


def make_runner():
    registry = ToolRegistry()
    registry.register(EchoTool())
    return ToolRunner(registry=registry, workspace=Path.cwd())


def test_query_loop_finishes_when_assistant_has_no_tools():
    client = FakeModelClient([AssistantTurn(text="final answer")])
    messages = []

    events = list(query_loop(messages, "system", client, make_runner()))

    assert events == [AssistantEvent(text="final answer")]
    assert messages[-1].role == "assistant"
    assert messages[-1].content == "final answer"
    assert client.call_count == 1
```

- [ ] **Step 2: 写失败测试，覆盖一次工具调用后继续模型**

追加：

```python
def test_query_loop_runs_tool_and_continues_to_final_answer():
    client = FakeModelClient(
        [
            AssistantTurn(
                text="",
                tool_uses=[ToolUse(id="toolu_1", name="echo", input={"text": "from tool"})],
            ),
            AssistantTurn(text="tool said: from tool"),
        ]
    )
    messages = []

    events = list(query_loop(messages, "system", client, make_runner()))

    assert events == [
        AssistantEvent(text=""),
        ToolResultEvent(name="echo", ok=True, preview="from tool"),
        AssistantEvent(text="tool said: from tool"),
    ]
    assert [message.role for message in messages] == ["assistant", "tool", "assistant"]
    assert client.call_count == 2
```

- [ ] **Step 3: 写失败测试，覆盖 max_turns**

追加：

```python
def test_query_loop_stops_at_max_turns():
    client = FakeModelClient(
        [
            AssistantTurn(text="", tool_uses=[ToolUse(id="toolu_1", name="echo", input={"text": "1"})]),
            AssistantTurn(text="", tool_uses=[ToolUse(id="toolu_2", name="echo", input={"text": "2"})]),
        ]
    )
    messages = []

    events = list(query_loop(messages, "system", client, make_runner(), max_turns=2))

    assert isinstance(events[-1], ErrorEvent)
    assert events[-1].message == "max_turns reached"
    assert client.call_count == 2
```

- [ ] **Step 4: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_query_loop.py -q`

Expected: FAIL，提示 `app.model_client` 或 `app.query_loop` 不存在。

- [ ] **Step 5: 实现 ModelClient 和 FakeModelClient**

`python_mvp/app/model_client.py` 内容：

```python
from __future__ import annotations

from typing import Protocol

from app.messages import AssistantTurn, Message


class ModelClient(Protocol):
    def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tools: list[dict],
    ) -> AssistantTurn:
        ...


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
```

- [ ] **Step 6: 实现 query_loop**

`python_mvp/app/query_loop.py` 内容：

```python
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
```

- [ ] **Step 7: 运行 phase 测试**

Run: `cd python_mvp && uv run pytest tests/test_query_loop.py tests/test_tool_runner.py -q`

Expected: PASS。

- [ ] **Step 8: Commit**

```bash
git add python_mvp/app/model_client.py python_mvp/app/query_loop.py python_mvp/tests/test_query_loop.py
git commit -m "feat: add fake query loop"
```

## Phase 验收

- [ ] `cd python_mvp && uv run pytest -q` 全部通过。
- [ ] `query_loop` 无工具调用时只调用一次模型。
- [ ] `query_loop` 有工具调用时会追加 assistant、tool、assistant 三类消息。
- [ ] 未知工具和工具异常不会抛出到 query loop 外层，而是生成 error tool message。
- [ ] `max_turns` 能阻止无限工具调用循环。

