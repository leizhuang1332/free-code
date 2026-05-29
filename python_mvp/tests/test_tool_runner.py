from pathlib import Path

from app.messages import ToolUse
from app.permissions import PermissionMode, PermissionPolicy, ToolCapability
from app.tool_registry import ToolContext, ToolRegistry, ToolResult
from app.tool_runner import ToolRunner


class EchoTool:
    name = "echo"
    description = "Return the provided text."
    capability = ToolCapability.READ

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


class ExplodingTool:
    name = "explode"
    description = "Raise an exception."
    capability = ToolCapability.READ

    def schema(self):
        return {"name": self.name, "description": self.description, "input_schema": {"type": "object"}}

    def run(self, input, context: ToolContext):
        raise RuntimeError("boom")


class WriteLikeTool:
    name = "write_like"
    description = "Pretend to write."
    capability = ToolCapability.WRITE

    def schema(self):
        return {"name": self.name, "description": self.description, "input_schema": {"type": "object"}}

    def run(self, input, context: ToolContext):
        return ToolResult(ok=True, content="wrote")


def test_tool_registry_registers_and_exports_schemas():
    registry = ToolRegistry()
    tool = EchoTool()

    registry.register(tool)

    assert registry.get("echo") is tool
    assert registry.schemas()[0]["name"] == "echo"


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
