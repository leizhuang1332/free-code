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
