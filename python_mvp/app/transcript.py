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
