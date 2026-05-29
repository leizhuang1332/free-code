from pathlib import Path

from app.messages import AssistantEvent, AssistantTurn, ErrorEvent, ToolResultEvent, ToolUse
from app.model_client import FakeModelClient
from app.permissions import ToolCapability
from app.query_loop import query_loop
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
