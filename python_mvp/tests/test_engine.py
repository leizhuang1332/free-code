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
