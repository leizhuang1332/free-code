# Phase 3 File Read Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加受 workspace 路径限制的 `list_dir` 和 `read_file`，让模型可以读取本地项目上下文，同时避免越权路径和超大文件。

**Architecture:** 文件访问能力放在 `app/tools/` 下，路径校验抽到 `path_guard.py`。工具仍通过 `ToolRegistry` 注册，并由现有 `ToolRunner` 串行执行。

**Tech Stack:** Python pathlib、uv、pytest、tmp_path fixture。

---

## 文件结构

- Create: `python_mvp/app/tools/__init__.py`
- Create: `python_mvp/app/tools/path_guard.py`
- Create: `python_mvp/app/tools/list_dir.py`
- Create: `python_mvp/app/tools/read_file.py`
- Create: `python_mvp/tests/test_file_tools.py`

## Task 1: Workspace 路径保护

**Files:**
- Create: `python_mvp/app/tools/path_guard.py`
- Create: `python_mvp/tests/test_file_tools.py`

- [ ] **Step 1: 写失败测试，覆盖合法路径和越权路径**

`python_mvp/tests/test_file_tools.py` 内容：

```python
from pathlib import Path

import pytest

from app.tools.path_guard import WorkspacePathError, resolve_workspace_path


def test_resolve_workspace_path_allows_relative_path_inside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "README.md"
    target.write_text("hello", encoding="utf-8")

    resolved = resolve_workspace_path(workspace, "README.md")

    assert resolved == target.resolve()


def test_resolve_workspace_path_rejects_parent_escape(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(WorkspacePathError, match="path escapes workspace"):
        resolve_workspace_path(workspace, "../secret.txt")


def test_resolve_workspace_path_rejects_absolute_escape(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(WorkspacePathError, match="path escapes workspace"):
        resolve_workspace_path(workspace, str(outside))
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_file_tools.py -q`

Expected: FAIL，提示 `app.tools.path_guard` 不存在。

- [ ] **Step 3: 实现路径保护**

`python_mvp/app/tools/path_guard.py` 内容：

```python
from __future__ import annotations

from pathlib import Path


class WorkspacePathError(ValueError):
    pass


def resolve_workspace_path(workspace: Path, raw_path: str) -> Path:
    root = workspace.resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate

    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise WorkspacePathError(f"path escapes workspace: {raw_path}") from exc

    return resolved
```

- [ ] **Step 4: 创建 tools 包标记**

`python_mvp/app/tools/__init__.py` 内容：

```python
"""Built-in MVP tools."""
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd python_mvp && uv run pytest tests/test_file_tools.py -q`

Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add python_mvp/app/tools/__init__.py python_mvp/app/tools/path_guard.py python_mvp/tests/test_file_tools.py
git commit -m "feat: add workspace path guard"
```

## Task 2: list_dir 工具

**Files:**
- Create: `python_mvp/app/tools/list_dir.py`
- Modify: `python_mvp/tests/test_file_tools.py`

- [ ] **Step 1: 写失败测试，覆盖目录列出、非目录、越权路径**

追加：

```python
from app.tool_registry import ToolContext
from app.tools.list_dir import ListDirTool


def test_list_dir_lists_names_sorted(tmp_path):
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "subdir").mkdir()
    tool = ListDirTool()

    result = tool.run({"path": "."}, ToolContext(workspace=tmp_path))

    assert result.ok is True
    assert result.content.splitlines() == ["a.txt", "b.txt", "subdir/"]


def test_list_dir_rejects_file_path(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    tool = ListDirTool()

    result = tool.run({"path": "a.txt"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "not a directory" in result.content


def test_list_dir_rejects_workspace_escape(tmp_path):
    tool = ListDirTool()

    result = tool.run({"path": ".."}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "path escapes workspace" in result.content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_file_tools.py -q`

Expected: FAIL，提示 `ListDirTool` 不存在。

- [ ] **Step 3: 实现 list_dir**

`python_mvp/app/tools/list_dir.py` 内容：

```python
from __future__ import annotations

from typing import Any

from app.tool_registry import ToolContext, ToolResult
from app.tools.path_guard import WorkspacePathError, resolve_workspace_path


class ListDirTool:
    name = "list_dir"
    description = "List files and directories inside the workspace."

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }

    def run(self, input: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_path = input.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            return ToolResult(ok=False, content="path must be a non-empty string")

        try:
            path = resolve_workspace_path(context.workspace, raw_path)
        except WorkspacePathError as exc:
            return ToolResult(ok=False, content=str(exc))

        if not path.exists():
            return ToolResult(ok=False, content=f"path does not exist: {raw_path}")
        if not path.is_dir():
            return ToolResult(ok=False, content=f"not a directory: {raw_path}")

        names = []
        for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
            suffix = "/" if child.is_dir() else ""
            names.append(f"{child.name}{suffix}")
        return ToolResult(ok=True, content="\n".join(names))
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python_mvp && uv run pytest tests/test_file_tools.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/tools/list_dir.py python_mvp/tests/test_file_tools.py
git commit -m "feat: add list_dir tool"
```

## Task 3: read_file 工具

**Files:**
- Create: `python_mvp/app/tools/read_file.py`
- Modify: `python_mvp/tests/test_file_tools.py`

- [ ] **Step 1: 写失败测试，覆盖读取、目录拒绝、大小限制、越权路径**

追加：

```python
from app.tools.read_file import ReadFileTool


def test_read_file_reads_text(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    tool = ReadFileTool(max_bytes=100)

    result = tool.run({"path": "README.md"}, ToolContext(workspace=tmp_path))

    assert result.ok is True
    assert result.content == "hello"


def test_read_file_rejects_directory(tmp_path):
    (tmp_path / "subdir").mkdir()
    tool = ReadFileTool(max_bytes=100)

    result = tool.run({"path": "subdir"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "not a file" in result.content


def test_read_file_rejects_large_file(tmp_path):
    (tmp_path / "large.txt").write_text("abcdef", encoding="utf-8")
    tool = ReadFileTool(max_bytes=5)

    result = tool.run({"path": "large.txt"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "file too large" in result.content


def test_read_file_rejects_workspace_escape(tmp_path):
    tool = ReadFileTool(max_bytes=100)

    result = tool.run({"path": "../secret.txt"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "path escapes workspace" in result.content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_file_tools.py -q`

Expected: FAIL，提示 `ReadFileTool` 不存在。

- [ ] **Step 3: 实现 read_file**

`python_mvp/app/tools/read_file.py` 内容：

```python
from __future__ import annotations

from typing import Any

from app.tool_registry import ToolContext, ToolResult
from app.tools.path_guard import WorkspacePathError, resolve_workspace_path


class ReadFileTool:
    name = "read_file"
    description = "Read a UTF-8 text file inside the workspace."

    def __init__(self, max_bytes: int = 64_000) -> None:
        self._max_bytes = max_bytes

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }

    def run(self, input: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_path = input.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            return ToolResult(ok=False, content="path must be a non-empty string")

        try:
            path = resolve_workspace_path(context.workspace, raw_path)
        except WorkspacePathError as exc:
            return ToolResult(ok=False, content=str(exc))

        if not path.exists():
            return ToolResult(ok=False, content=f"path does not exist: {raw_path}")
        if not path.is_file():
            return ToolResult(ok=False, content=f"not a file: {raw_path}")
        if path.stat().st_size > self._max_bytes:
            return ToolResult(ok=False, content=f"file too large: {raw_path}")

        try:
            return ToolResult(ok=True, content=path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            return ToolResult(ok=False, content=f"file is not valid UTF-8 text: {raw_path}")
```

- [ ] **Step 4: 运行 phase 测试**

Run: `cd python_mvp && uv run pytest tests/test_file_tools.py tests/test_tool_runner.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/tools/read_file.py python_mvp/tests/test_file_tools.py
git commit -m "feat: add read_file tool"
```

## Task 4: 工具注册工厂

**Files:**
- Modify: `python_mvp/app/tools/__init__.py`
- Create: `python_mvp/tests/test_builtin_tools.py`

- [ ] **Step 1: 写失败测试，验证内置只读工具注册**

`python_mvp/tests/test_builtin_tools.py` 内容：

```python
from app.tools import create_read_only_registry


def test_create_read_only_registry_registers_file_tools():
    registry = create_read_only_registry()

    assert registry.get("list_dir") is not None
    assert registry.get("read_file") is not None
    assert [schema["name"] for schema in registry.schemas()] == ["list_dir", "read_file"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_builtin_tools.py -q`

Expected: FAIL，提示 `create_read_only_registry` 不存在。

- [ ] **Step 3: 实现注册工厂**

`python_mvp/app/tools/__init__.py` 内容：

```python
"""Built-in MVP tools."""

from app.tool_registry import ToolRegistry
from app.tools.list_dir import ListDirTool
from app.tools.read_file import ReadFileTool


def create_read_only_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ListDirTool())
    registry.register(ReadFileTool())
    return registry
```

- [ ] **Step 4: 全量测试**

Run: `cd python_mvp && uv run pytest -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/tools/__init__.py python_mvp/tests/test_builtin_tools.py
git commit -m "feat: register built-in read tools"
```

## Phase 验收

- [ ] `list_dir` 和 `read_file` 的所有路径都被限制在 workspace 内。
- [ ] `read_file` 有明确大小限制和 UTF-8 错误提示。
- [ ] `create_read_only_registry()` 默认只注册读工具。
- [ ] `cd python_mvp && uv run pytest -q` 全部通过。

