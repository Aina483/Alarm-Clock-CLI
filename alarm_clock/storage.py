"""JSON-backed persistence for alarms."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .models import Alarm


DEFAULT_STORE_PATH = Path("data/alarms.json")


class AlarmStore:
    def __init__(self, path: Path = DEFAULT_STORE_PATH):
        self.path = Path(path)

    def load(self) -> List[Alarm]:
        """
        Load alarms from disk.

        Missing file is treated as an empty alarm collection.
        Corrupted JSON raises a clear error instead of silently
        deleting/resetting the user's alarms.
        """
        #  missing file -> no alarms.
        if not self.path.exists():
            return []

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            #corrupted JSON now fails loudly.
            raise ValueError(
                f"Alarm storage is corrupted: {self.path}"
            ) from exc
        except OSError as exc:
            # filesystem errors are surfaced instead of
            # being silently treated as an empty alarm list.
            raise RuntimeError(
                f"Could not read alarm storage: {self.path}"
            ) from exc

        if not isinstance(raw, list):
            #validate the expected JSON structure.
            raise ValueError(
                f"Invalid alarm storage format: expected a JSON list in {self.path}"
            )

        try:
            return [Alarm.from_dict(item) for item in raw]
        except (TypeError, KeyError) as exc:
            # malformed alarm records fail loudly.
            raise ValueError(
                f"Invalid alarm record in storage: {self.path}"
            ) from exc

    def save(self, alarms: List[Alarm]) -> None:
        """
        Persist all alarms.

        The directory/file is created lazily on the first save.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = [alarm.to_dict() for alarm in alarms]

        # EXISTING: atomic-ish temp-file replacement is retained.
        # It is not required by the assignment, but it is a useful
        # safety improvement and does not conflict with the design.
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(self.path)

    def get_file_mtime(self) -> float | None:
        """
        Return the storage file modification time.

        This is deliberately a filesystem concern only.
        The storage layer does not know anything about scheduling.
        """
        #used by scheduler's mtime cache.
        try:
            return self.path.stat().st_mtime
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise RuntimeError(
                f"Could not inspect alarm storage: {self.path}"
            ) from exc