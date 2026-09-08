"""JSON-backed persistence for alarms.

A single JSON file, read fully and rewritten fully on each
mutation. Alarm counts for a personal CLI tool are small (tens, not
thousands), so there's no need for incremental writes, locking, or a real
database — that complexity was explicitly out of scope anyway.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from .models import Alarm

DEFAULT_STORE_PATH = Path(os.path.expanduser("~/.alarm_clock/alarms.json"))


class AlarmStore:
    def __init__(self, path: Path = DEFAULT_STORE_PATH):
        self.path = Path(path)

    def load(self) -> List[Alarm]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            # A corrupted or partial file shouldn't crash the whole app - treat
            # it as empty and let the user re-add alarms.
            print(f"Warning: could not read {self.path}, starting fresh.")
            return []
        return [Alarm.from_dict(item) for item in raw]

    def save(self, alarms: List[Alarm]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [a.to_dict() for a in alarms]
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2))
        tmp_path.replace(self.path)  # avoid a half written file
