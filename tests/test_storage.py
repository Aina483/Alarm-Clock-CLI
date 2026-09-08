from pathlib import Path

from alarm_clock.models import Alarm
from alarm_clock.storage import AlarmStore


def test_save_and_load_roundtrip(tmp_path):
    store = AlarmStore(path=tmp_path / "alarms.json")
    alarm = Alarm.new("07:30", "Wake up", "daily", 5)
    store.save([alarm])

    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].id == alarm.id
    assert loaded[0].time == "07:30"
    assert loaded[0].label == "Wake up"


def test_load_missing_file_returns_empty_list(tmp_path):
    store = AlarmStore(path=tmp_path / "does_not_exist.json")
    assert store.load() == []


def test_load_corrupted_file_returns_empty_list(tmp_path):
    p = tmp_path / "alarms.json"
    p.write_text("{not valid json")
    store = AlarmStore(path=p)
    assert store.load() == []


def test_save_creates_parent_directory(tmp_path):
    nested = tmp_path / "nested" / "dir" / "alarms.json"
    store = AlarmStore(path=nested)
    store.save([Alarm.new("06:00", "Test", "once", 5)])
    assert nested.exists()
