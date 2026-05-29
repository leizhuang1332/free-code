# Phase 4 REPL And Transcript Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加可人工连续对话的 `uv run python -m app.repl`，支持 `/help`、`/clear` 本地命令，并把 user、assistant、tool_result 顺序写入 JSONL transcript。

**Architecture:** `SessionEngine` 作为 REPL 和 query loop 中间层，负责输入处理、messages 状态、事件转发和 transcript 写入。REPL 只负责 stdin/stdout，不持有业务状态。

**Tech Stack:** Python dataclasses、uv、json/jsonlines 风格写入、pytest、tmp_path。

---

## 文件结构

- Create: `python_mvp/app/input_processor.py`
- Create: `python_mvp/app/transcript.py`
- Create: `python_mvp/app/engine.py`
- Create: `python_mvp/app/repl.py`
- Create: `python_mvp/tests/test_input_processor.py`
- Create: `python_mvp/tests/test_transcript.py`
- Create: `python_mvp/tests/test_engine.py`

## Task 1: 输入处理

**Files:**
- Create: `python_mvp/app/input_processor.py`
- Create: `python_mvp/tests/test_input_processor.py`

- [ ] **Step 1: 写失败测试，覆盖普通文本、/help、/clear**

`python_mvp/tests/test_input_processor.py` 内容：

```python
from app.input_processor import process_user_input


def test_process_user_input_turns_plain_text_into_user_message():
    processed = process_user_input("hello")

    assert processed.should_query is True
    assert processed.clear_messages is False
    assert processed.local_output is None
    assert processed.messages[0].role == "user"
    assert processed.messages[0].content == "hello"


def test_process_user_input_help_is_local_command():
    processed = process_user_input("/help")

    assert processed.should_query is False
    assert processed.local_output == "Commands: /help, /clear, /exit"
    assert processed.messages == []


def test_process_user_input_clear_is_local_command_with_clear_intent():
    processed = process_user_input("/clear")

    assert processed.should_query is False
    assert processed.clear_messages is True
    assert processed.local_output == "Conversation cleared."
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_input_processor.py -q`

Expected: FAIL，提示 `app.input_processor` 不存在。

- [ ] **Step 3: 实现 input_processor**

`python_mvp/app/input_processor.py` 内容：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python_mvp && uv run pytest tests/test_input_processor.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/input_processor.py python_mvp/tests/test_input_processor.py
git commit -m "feat: add input processor"
```

## Task 2: TranscriptStore JSONL

**Files:**
- Create: `python_mvp/app/transcript.py`
- Create: `python_mvp/tests/test_transcript.py`

- [ ] **Step 1: 写失败测试，验证 JSONL 写入**

`python_mvp/tests/test_transcript.py` 内容：

```python
import json

from app.messages import Message
from app.transcript import TranscriptStore


def test_transcript_store_appends_message_records(tmp_path):
    path = tmp_path / "session.jsonl"
    store = TranscriptStore(path)

    store.append_message("user", Message(role="user", content="hello"))
    store.append_message("assistant", Message(role="assistant", content="hi"))

    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["type"] == "user"
    assert records[0]["message"]["role"] == "user"
    assert records[0]["message"]["content"] == "hello"
    assert records[1]["type"] == "assistant"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_transcript.py -q`

Expected: FAIL，提示 `TranscriptStore` 不存在。

- [ ] **Step 3: 实现 TranscriptStore**

`python_mvp/app/transcript.py` 内容：

```python
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.messages import Message


class TranscriptStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append_message(self, record_type: str, message: Message) -> None:
        record = {
            "type": record_type,
            "message": asdict(message),
        }
        with self._path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python_mvp && uv run pytest tests/test_transcript.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/transcript.py python_mvp/tests/test_transcript.py
git commit -m "feat: add transcript store"
```

## Task 3: SessionEngine

**Files:**
- Create: `python_mvp/app/engine.py`
- Create: `python_mvp/tests/test_engine.py`

- [ ] **Step 1: 写失败测试，覆盖普通输入、transcript、local command**

`python_mvp/tests/test_engine.py` 内容：

```python
import json
from pathlib import Path

from app.engine import SessionEngine
from app.messages import AssistantEvent, AssistantTurn
from app.model_client import FakeModelClient
from app.tool_registry import ToolRegistry
from app.tool_runner import ToolRunner
from app.transcript import TranscriptStore


def make_engine(tmp_path, turns):
    registry = ToolRegistry()
    return SessionEngine(
        model_client=FakeModelClient(turns),
        tool_runner=ToolRunner(registry=registry, workspace=Path.cwd()),
        transcript=TranscriptStore(tmp_path / "session.jsonl"),
        system_prompt="system",
    )


def test_session_engine_appends_user_and_assistant_messages(tmp_path):
    engine = make_engine(tmp_path, [AssistantTurn(text="hello user")])

    events = list(engine.submit("hi"))

    assert events == [AssistantEvent(text="hello user")]
    assert [message.role for message in engine.messages] == ["user", "assistant"]


def test_session_engine_writes_transcript(tmp_path):
    engine = make_engine(tmp_path, [AssistantTurn(text="hello user")])

    list(engine.submit("hi"))

    records = [
        json.loads(line)
        for line in (tmp_path / "session.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [record["type"] for record in records] == ["user", "assistant"]


def test_session_engine_local_command_does_not_call_model(tmp_path):
    engine = make_engine(tmp_path, [])

    events = list(engine.submit("/help"))

    assert [event.text for event in events] == ["Commands: /help, /clear, /exit"]
    assert engine.messages == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_engine.py -q`

Expected: FAIL，提示 `SessionEngine` 不存在。

- [ ] **Step 3: 实现 SessionEngine**

`python_mvp/app/engine.py` 内容：

```python
from __future__ import annotations

from collections.abc import Iterator

from app.input_processor import process_user_input
from app.messages import AssistantEvent, Message, QueryEvent, ToolResultEvent
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python_mvp && uv run pytest tests/test_engine.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/engine.py python_mvp/tests/test_engine.py
git commit -m "feat: add session engine"
```

## Task 4: REPL 入口

**Files:**
- Create: `python_mvp/app/repl.py`

- [ ] **Step 1: 实现 REPL**

`python_mvp/app/repl.py` 内容：

```python
from __future__ import annotations

from pathlib import Path

from app.engine import SessionEngine
from app.messages import AssistantEvent, ErrorEvent, ToolResultEvent
from app.model_client import DeepSeekOpenAIClient
from app.tool_runner import ToolRunner
from app.tools import create_read_only_registry
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
    registry = create_read_only_registry()
    return SessionEngine(
        model_client=DeepSeekOpenAIClient.from_env(),
        tool_runner=ToolRunner(registry=registry, workspace=workspace),
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

        for event in engine.submit(text):
            rendered = render_event(event)
            if rendered:
                print(rendered)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行语法检查**

Run: `cd python_mvp && uv run python -m py_compile app/repl.py`

Expected: 无输出，退出码 0。

- [ ] **Step 3: 全量测试**

Run: `cd python_mvp && uv run pytest -q`

Expected: PASS。

- [ ] **Step 4: 人工冒烟测试**

Run: `cd python_mvp && uv run python -m app.repl`

Expected:

```text
> /help
Commands: /help, /clear, /exit
> /clear
Conversation cleared.
> /exit
```

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/repl.py
git commit -m "feat: add minimal repl"
```

## Phase 验收

- [ ] `cd python_mvp && uv run python -m app.repl` 可以启动。
- [ ] `/help` 和 `/clear` 不调用模型。
- [ ] 普通输入会追加 user message 并进入 query loop。
- [ ] `.mvp-session.jsonl` 能记录 user、assistant、tool_result 顺序。
- [ ] `cd python_mvp && uv run pytest -q` 全部通过。

