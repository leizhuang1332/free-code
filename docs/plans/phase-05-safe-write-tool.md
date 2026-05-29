# Phase 5 Safe Write Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加默认受限的 `write_file`，并用 `PermissionPolicy` 明确 `READ_ONLY` 拒绝写入、`ALLOW_ALL` 允许写入，为后续交互审批和真实 shell 权限打基础。

**Architecture:** 权限判断放在 `permissions.py`，工具声明能力，`ToolRunner` 在调用工具前统一检查权限。`write_file` 仍使用 workspace path guard，且不会创建 workspace 外路径。

**Tech Stack:** Python Enum、pathlib、uv、pytest、tmp_path。

---

## 文件结构

- Create: `python_mvp/app/permissions.py`
- Modify: `python_mvp/app/tool_registry.py`，增加工具 capability。
- Modify: `python_mvp/app/tool_runner.py`，接入权限策略。
- Create: `python_mvp/app/tools/write_file.py`
- Modify: `python_mvp/app/tools/__init__.py`，增加显式 all-tools 注册工厂。
- Create: `python_mvp/tests/test_permissions.py`
- Create: `python_mvp/tests/test_write_file_tool.py`

## Task 1: 权限模型

**Files:**
- Create: `python_mvp/app/permissions.py`
- Create: `python_mvp/tests/test_permissions.py`

- [ ] **Step 1: 写失败测试，覆盖三种模式**

`python_mvp/tests/test_permissions.py` 内容：

```python
from app.permissions import PermissionMode, PermissionPolicy, ToolCapability


def test_allow_all_allows_every_capability():
    policy = PermissionPolicy(PermissionMode.ALLOW_ALL)

    assert policy.can_use_tool("read_file", ToolCapability.READ) is True
    assert policy.can_use_tool("write_file", ToolCapability.WRITE) is True
    assert policy.can_use_tool("shell", ToolCapability.EXECUTE) is True


def test_read_only_allows_read_and_denies_write_execute():
    policy = PermissionPolicy(PermissionMode.READ_ONLY)

    assert policy.can_use_tool("read_file", ToolCapability.READ) is True
    assert policy.can_use_tool("write_file", ToolCapability.WRITE) is False
    assert policy.can_use_tool("shell", ToolCapability.EXECUTE) is False


def test_deny_all_denies_every_capability():
    policy = PermissionPolicy(PermissionMode.DENY_ALL)

    assert policy.can_use_tool("read_file", ToolCapability.READ) is False
    assert policy.can_use_tool("write_file", ToolCapability.WRITE) is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_permissions.py -q`

Expected: FAIL，提示 `app.permissions` 不存在。

- [ ] **Step 3: 实现 permissions.py**

`python_mvp/app/permissions.py` 内容：

```python
from __future__ import annotations

from enum import Enum


class PermissionMode(Enum):
    ALLOW_ALL = "allow_all"
    READ_ONLY = "read_only"
    DENY_ALL = "deny_all"


class ToolCapability(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


class PermissionPolicy:
    def __init__(self, mode: PermissionMode) -> None:
        self.mode = mode

    def can_use_tool(self, tool_name: str, capability: ToolCapability) -> bool:
        if self.mode == PermissionMode.ALLOW_ALL:
            return True
        if self.mode == PermissionMode.DENY_ALL:
            return False
        if self.mode == PermissionMode.READ_ONLY:
            return capability == ToolCapability.READ
        return False
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd python_mvp && uv run pytest tests/test_permissions.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/permissions.py python_mvp/tests/test_permissions.py
git commit -m "feat: add permission policy"
```

## Task 2: ToolRunner 接入权限

**Files:**
- Modify: `python_mvp/app/tool_registry.py`
- Modify: `python_mvp/app/tool_runner.py`
- Modify: `python_mvp/app/tools/list_dir.py`
- Modify: `python_mvp/app/tools/read_file.py`
- Modify: `python_mvp/tests/test_tool_runner.py`

- [ ] **Step 1: 给工具协议增加 capability**

在 `python_mvp/app/tool_registry.py` 中 import：

```python
from app.permissions import ToolCapability
```

在 `Tool` protocol 内增加：

```python
    capability: ToolCapability
```

- [ ] **Step 2: 给只读工具声明 capability**

在 `ListDirTool` 和 `ReadFileTool` 类中增加：

```python
    capability = ToolCapability.READ
```

并在对应文件 import：

```python
from app.permissions import ToolCapability
```

- [ ] **Step 3: 写失败测试，覆盖 READ_ONLY 拒绝写能力**

追加到 `python_mvp/tests/test_tool_runner.py`：

```python
from app.permissions import PermissionMode, PermissionPolicy, ToolCapability


class WriteLikeTool:
    name = "write_like"
    description = "Pretend to write."
    capability = ToolCapability.WRITE

    def schema(self):
        return {"name": self.name, "description": self.description, "input_schema": {"type": "object"}}

    def run(self, input, context: ToolContext):
        return ToolResult(ok=True, content="wrote")


def test_tool_runner_denies_tool_when_policy_rejects_capability():
    registry = ToolRegistry()
    registry.register(WriteLikeTool())
    runner = ToolRunner(
        registry=registry,
        workspace=Path.cwd(),
        permission_policy=PermissionPolicy(PermissionMode.READ_ONLY),
    )

    messages = runner.run_all([ToolUse(id="toolu_1", name="write_like", input={})])

    assert messages[0].is_error is True
    assert "permission denied" in messages[0].content
    assert "READ_ONLY" in messages[0].content
```

- [ ] **Step 4: 修改现有测试替身 capability**

在 `EchoTool` 和 `ExplodingTool` 上增加：

```python
    capability = ToolCapability.READ
```

- [ ] **Step 5: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_tool_runner.py -q`

Expected: FAIL，提示 `ToolRunner.__init__` 不支持 `permission_policy` 或没有权限拒绝逻辑。

- [ ] **Step 6: 修改 ToolRunner**

`ToolRunner.__init__` 改为：

```python
from app.permissions import PermissionMode, PermissionPolicy


class ToolRunner:
    def __init__(
        self,
        registry: ToolRegistry,
        workspace: Path,
        permission_policy: PermissionPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._context = ToolContext(workspace=workspace)
        self._permission_policy = permission_policy or PermissionPolicy(PermissionMode.ALLOW_ALL)
```

在 `_run_one` 找到 tool 后、执行 tool 前增加：

```python
        if not self._permission_policy.can_use_tool(tool.name, tool.capability):
            return self._tool_message(
                tool_use,
                f"permission denied for {tool.name} in {self._permission_policy.mode.name}",
                is_error=True,
            )
```

- [ ] **Step 7: 运行测试**

Run: `cd python_mvp && uv run pytest tests/test_tool_runner.py tests/test_file_tools.py -q`

Expected: PASS。

- [ ] **Step 8: Commit**

```bash
git add python_mvp/app/tool_registry.py python_mvp/app/tool_runner.py python_mvp/app/tools/list_dir.py python_mvp/app/tools/read_file.py python_mvp/tests/test_tool_runner.py
git commit -m "feat: enforce tool permissions"
```

## Task 3: write_file 工具

**Files:**
- Create: `python_mvp/app/tools/write_file.py`
- Create: `python_mvp/tests/test_write_file_tool.py`

- [ ] **Step 1: 写失败测试，覆盖写入、新目录、越权路径、非法 input**

`python_mvp/tests/test_write_file_tool.py` 内容：

```python
from app.tool_registry import ToolContext
from app.tools.write_file import WriteFileTool


def test_write_file_writes_utf8_text(tmp_path):
    tool = WriteFileTool(max_bytes=100)

    result = tool.run({"path": "notes/a.txt", "content": "hello"}, ToolContext(workspace=tmp_path))

    assert result.ok is True
    assert result.content == "wrote notes/a.txt"
    assert (tmp_path / "notes" / "a.txt").read_text(encoding="utf-8") == "hello"


def test_write_file_rejects_workspace_escape(tmp_path):
    tool = WriteFileTool(max_bytes=100)

    result = tool.run({"path": "../secret.txt", "content": "secret"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "path escapes workspace" in result.content


def test_write_file_rejects_large_content(tmp_path):
    tool = WriteFileTool(max_bytes=5)

    result = tool.run({"path": "large.txt", "content": "abcdef"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "content too large" in result.content


def test_write_file_rejects_missing_content(tmp_path):
    tool = WriteFileTool(max_bytes=100)

    result = tool.run({"path": "a.txt"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "content must be a string" in result.content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd python_mvp && uv run pytest tests/test_write_file_tool.py -q`

Expected: FAIL，提示 `WriteFileTool` 不存在。

- [ ] **Step 3: 实现 write_file**

`python_mvp/app/tools/write_file.py` 内容：

```python
from __future__ import annotations

from typing import Any

from app.permissions import ToolCapability
from app.tool_registry import ToolContext, ToolResult
from app.tools.path_guard import WorkspacePathError, resolve_workspace_path


class WriteFileTool:
    name = "write_file"
    description = "Write UTF-8 text to a file inside the workspace."
    capability = ToolCapability.WRITE

    def __init__(self, max_bytes: int = 64_000) -> None:
        self._max_bytes = max_bytes

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        }

    def run(self, input: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_path = input.get("path")
        content = input.get("content")
        if not isinstance(raw_path, str) or not raw_path:
            return ToolResult(ok=False, content="path must be a non-empty string")
        if not isinstance(content, str):
            return ToolResult(ok=False, content="content must be a string")
        if len(content.encode("utf-8")) > self._max_bytes:
            return ToolResult(ok=False, content=f"content too large: {raw_path}")

        try:
            path = resolve_workspace_path(context.workspace, raw_path)
        except WorkspacePathError as exc:
            return ToolResult(ok=False, content=str(exc))

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(ok=True, content=f"wrote {raw_path}")
```

- [ ] **Step 4: 运行测试**

Run: `cd python_mvp && uv run pytest tests/test_write_file_tool.py -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/tools/write_file.py python_mvp/tests/test_write_file_tool.py
git commit -m "feat: add write_file tool"
```

## Task 4: 注册写工具但默认 REPL 仍只读

**Files:**
- Modify: `python_mvp/app/tools/__init__.py`
- Modify: `python_mvp/app/repl.py`
- Create: `python_mvp/tests/test_builtin_tools.py`

- [ ] **Step 1: 扩展注册工厂**

`python_mvp/app/tools/__init__.py` 改为：

```python
"""Built-in MVP tools."""

from app.tool_registry import ToolRegistry
from app.tools.list_dir import ListDirTool
from app.tools.read_file import ReadFileTool
from app.tools.write_file import WriteFileTool


def create_read_only_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ListDirTool())
    registry.register(ReadFileTool())
    return registry


def create_all_tools_registry() -> ToolRegistry:
    registry = create_read_only_registry()
    registry.register(WriteFileTool())
    return registry
```

- [ ] **Step 2: 修改内置工具测试**

`python_mvp/tests/test_builtin_tools.py` 改为：

```python
from app.tools import create_all_tools_registry, create_read_only_registry


def test_create_read_only_registry_registers_file_tools():
    registry = create_read_only_registry()

    assert [schema["name"] for schema in registry.schemas()] == ["list_dir", "read_file"]


def test_create_all_tools_registry_includes_write_file():
    registry = create_all_tools_registry()

    assert [schema["name"] for schema in registry.schemas()] == ["list_dir", "read_file", "write_file"]
```

- [ ] **Step 3: REPL 显式使用 READ_ONLY policy**

在 `python_mvp/app/repl.py` import：

```python
from app.permissions import PermissionMode, PermissionPolicy
```

把 `ToolRunner(...)` 改为：

```python
        tool_runner=ToolRunner(
            registry=registry,
            workspace=workspace,
            permission_policy=PermissionPolicy(PermissionMode.READ_ONLY),
        ),
```

- [ ] **Step 4: 全量测试**

Run: `cd python_mvp && uv run pytest -q`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add python_mvp/app/tools/__init__.py python_mvp/app/repl.py python_mvp/tests/test_builtin_tools.py
git commit -m "feat: expose write tool behind permissions"
```

## Phase 验收

- [ ] `READ_ONLY` 模式允许 `list_dir`、`read_file`，拒绝 `write_file`。
- [ ] `ALLOW_ALL` 模式允许 `write_file`。
- [ ] `write_file` 不能写出 workspace。
- [ ] REPL 默认仍然只读，不默认开放写文件。
- [ ] `cd python_mvp && uv run pytest -q` 全部通过。

