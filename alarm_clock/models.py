"""
This is the data model for a single alarm.
Design decision : Alarms are plain dataclass serialized to/from a dict for JSON storage since the
assessment explicitelt rules out the use of DB.

Flat JSON file is simplest thing that can persist state across run
"""


from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional, List
import itertools
import uuid


# Repest modes are supported
REPEAT_ONCE = "once"
REPEAT_DAILY = "daily"
REPEAT_WEEKDAYS = "weekdays"  # Mon-Fri
REPEAT_WEEKENDS = "weekends"  # Sat-Sun
VALID_REPEATS = {REPEAT_ONCE, REPEAT_DAILY, REPEAT_WEEKDAYS, REPEAT_WEEKENDS}


@dataclass
class Alarm:
    id: str
    time: str  # "HH:MM", 24-hour, stored as string for simple JSON round-trip
    label: str = "Alarm"
    repeat: str = REPEAT_ONCE
    enabled: bool = True
    snooze_minutes: int = 5

    # Runtime/state fields, not user-supplied at creation time.
    last_triggered_on: Optional[str] = None  # ISO date string, dedups firing within a day
    snoozed_until: Optional[str] = None  # ISO datetime string, set when snoozed

    @staticmethod
    def new(time: str, label: str, repeat: str, snooze_minutes: int) -> "Alarm":
        return Alarm(
            id=uuid.uuid4().hex[:8],
            time=time,
            label=label,
            repeat=repeat,
            snooze_minutes=snooze_minutes,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Alarm":
        return Alarm(**d)
