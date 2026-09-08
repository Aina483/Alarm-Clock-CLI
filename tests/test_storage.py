import json

import pytest

from alarm_clock.models import Alarm
from alarm_clock.storage import AlarmStore


def test_save_and_load_roundtrip(tmp_path):
    store = AlarmStore(
        path=tmp_path / "alarms.json"
    )

    alarm = Alarm.new(
        "07:30",
        "Wake up",
        "daily",
        5,
    )

    store.save([alarm])

    loaded = store.load()

    assert len(loaded) == 1
    assert loaded[0].id == alarm.id
    assert loaded[0].time == "07:30"
    assert loaded[0].label == "Wake up"
    assert loaded[0].repeat == "daily"
    assert loaded[0].snooze_minutes == 5


def test_load_missing_file_returns_empty_list(tmp_path):
    store = AlarmStore(
        path=tmp_path / "does_not_exist.json"
    )

    assert store.load() == []



# Corrupt storage must fail loudly rather than silently
# resetting the user's alarms.
def test_load_corrupted_file_raises_error(tmp_path):
    p = tmp_path / "alarms.json"

    p.write_text(
        "{not valid json",
        encoding="utf-8",
    )

    store = AlarmStore(path=p)

    with pytest.raises(ValueError, match="corrupted"):
        store.load()


def test_load_invalid_json_structure_raises_error(tmp_path):
    p = tmp_path / "alarms.json"

    p.write_text(
        json.dumps({"alarm": "invalid"}),
        encoding="utf-8",
    )

    store = AlarmStore(path=p)

    with pytest.raises(
        ValueError,
        match="expected a JSON list",
    ):
        store.load()


def test_save_creates_parent_directory(tmp_path):
    nested = (
        tmp_path
        / "nested"
        / "dir"
        / "alarms.json"
    )

    store = AlarmStore(path=nested)

    store.save(
        [Alarm.new(
            "06:00",
            "Test",
            "once",
            5,
        )]
    )

    assert nested.exists()



def test_save_creates_file_lazily(tmp_path):
    path = tmp_path / "alarms.json"

    store = AlarmStore(path=path)

    assert not path.exists()

    store.save([])

    assert path.exists()



def test_get_file_mtime_returns_none_when_missing(tmp_path):
    path = tmp_path / "alarms.json"

    store = AlarmStore(path=path)

    assert store.get_file_mtime() is None



def test_get_file_mtime_returns_value_after_save(tmp_path):
    path = tmp_path / "alarms.json"

    store = AlarmStore(path=path)

    store.save([])

    mtime = store.get_file_mtime()

    assert mtime is not None
    assert isinstance(mtime, float)