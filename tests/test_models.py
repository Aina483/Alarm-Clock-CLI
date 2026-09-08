from datetime import datetime

import pytest

from alarm_clock.models import (
    Alarm,
    REPEAT_ONCE,
    REPEAT_DAILY,
    REPEAT_WEEKDAYS,
    REPEAT_WEEKENDS,
    VALID_REPEATS,
)


def test_create_alarm():
    alarm = Alarm(
        id="abc123",
        time="07:30",
        label="Wake up",
        repeat=REPEAT_ONCE,
        enabled=True,
        snooze_minutes=5,
    )

    assert alarm.id == "abc123"
    assert alarm.time == "07:30"
    assert alarm.label == "Wake up"
    assert alarm.repeat == REPEAT_ONCE
    assert alarm.enabled is True
    assert alarm.snooze_minutes == 5
    assert alarm.last_triggered_on is None
    assert alarm.snoozed_until is None


def test_alarm_defaults():
    alarm = Alarm(
        id="abc123",
        time="07:30",
    )

    assert alarm.label == "Alarm"
    assert alarm.repeat == REPEAT_ONCE
    assert alarm.enabled is True
    assert alarm.snooze_minutes == 5
    assert alarm.last_triggered_on is None
    assert alarm.snoozed_until is None


def test_new_creates_alarm_with_unique_id():
    alarm1 = Alarm.new(
        time="07:30",
        label="Wake up",
        repeat=REPEAT_DAILY,
        snooze_minutes=5,
    )

    alarm2 = Alarm.new(
        time="08:00",
        label="Meeting",
        repeat=REPEAT_ONCE,
        snooze_minutes=10,
    )

    assert alarm1.id != alarm2.id
    assert len(alarm1.id) == 8
    assert len(alarm2.id) == 8


def test_new_creates_alarm_with_correct_values():
    alarm = Alarm.new(
        time="07:30",
        label="Wake up",
        repeat=REPEAT_DAILY,
        snooze_minutes=10,
    )

    assert alarm.time == "07:30"
    assert alarm.label == "Wake up"
    assert alarm.repeat == REPEAT_DAILY
    assert alarm.snooze_minutes == 10
    assert alarm.enabled is True


def test_to_dict_serializes_alarm():
    alarm = Alarm(
        id="abc123",
        time="07:30",
        label="Wake up",
        repeat=REPEAT_DAILY,
        enabled=True,
        snooze_minutes=5,
        last_triggered_on="2026-09-08",
        snoozed_until="2026-09-08T07:35:00",
    )

    data = alarm.to_dict()

    assert data == {
        "id": "abc123",
        "time": "07:30",
        "label": "Wake up",
        "repeat": REPEAT_DAILY,
        "enabled": True,
        "snooze_minutes": 5,
        "last_triggered_on": "2026-09-08",
        "snoozed_until": "2026-09-08T07:35:00",
    }


def test_from_dict_deserializes_alarm():
    data = {
        "id": "abc123",
        "time": "07:30",
        "label": "Wake up",
        "repeat": REPEAT_DAILY,
        "enabled": True,
        "snooze_minutes": 5,
        "last_triggered_on": "2026-09-08",
        "snoozed_until": "2026-09-08T07:35:00",
    }

    alarm = Alarm.from_dict(data)

    assert alarm.id == "abc123"
    assert alarm.time == "07:30"
    assert alarm.label == "Wake up"
    assert alarm.repeat == REPEAT_DAILY
    assert alarm.enabled is True
    assert alarm.snooze_minutes == 5
    assert alarm.last_triggered_on == "2026-09-08"
    assert alarm.snoozed_until == "2026-09-08T07:35:00"


def test_alarm_round_trip_serialization():
    original = Alarm(
        id="abc123",
        time="07:30",
        label="Wake up",
        repeat=REPEAT_DAILY,
        enabled=True,
        snooze_minutes=5,
        last_triggered_on="2026-09-08",
        snoozed_until="2026-09-08T07:35:00",
    )

    serialized = original.to_dict()
    restored = Alarm.from_dict(serialized)

    assert restored == original


def test_valid_repeat_modes():
    assert REPEAT_ONCE in VALID_REPEATS
    assert REPEAT_DAILY in VALID_REPEATS
    assert REPEAT_WEEKDAYS in VALID_REPEATS
    assert REPEAT_WEEKENDS in VALID_REPEATS

    assert len(VALID_REPEATS) == 4