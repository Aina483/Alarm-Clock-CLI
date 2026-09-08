from datetime import datetime, timedelta

from alarm_clock.models import Alarm, REPEAT_ONCE, REPEAT_DAILY, REPEAT_WEEKDAYS, REPEAT_WEEKENDS
from alarm_clock.schedular import is_due, mark_triggered, snooze, dismiss, next_occurrence


def make_alarm(**overrides):
    base = dict(id="abc123", time="07:00", label="Test", repeat=REPEAT_ONCE, snooze_minutes=5)
    base.update(overrides)
    return Alarm(**base)


def test_fires_at_exact_time():
    alarm = make_alarm(time="07:00")
    now = datetime(2026, 9, 7, 7, 0)
    assert is_due(alarm, now) is True


def test_does_not_fire_at_wrong_minute():
    alarm = make_alarm(time="07:00")
    now = datetime(2026, 9, 7, 7, 1)
    assert is_due(alarm, now) is False


def test_disabled_alarm_never_due():
    alarm = make_alarm(time="07:00", enabled=False)
    now = datetime(2026, 9, 7, 7, 0)
    assert is_due(alarm, now) is False


def test_does_not_refire_same_day_after_trigger():
    alarm = make_alarm(time="07:00", repeat=REPEAT_DAILY)
    now = datetime(2026, 9, 7, 7, 0)
    assert is_due(alarm, now) is True
    mark_triggered(alarm, now)
    # still 07:00, same day, same minute window -> should not fire again
    assert is_due(alarm, now) is False


def test_daily_fires_again_next_day():
    alarm = make_alarm(time="07:00", repeat=REPEAT_DAILY)
    day1 = datetime(2026, 9, 7, 7, 0)
    mark_triggered(alarm, day1)
    day2 = datetime(2026, 9, 8, 7, 0)
    assert is_due(alarm, day2) is True


def test_weekdays_skips_saturday():
    alarm = make_alarm(time="08:00", repeat=REPEAT_WEEKDAYS)
    saturday = datetime(2026, 9, 12, 8, 0)  # confirmed Saturday
    assert saturday.weekday() == 5
    assert is_due(alarm, saturday) is False


def test_weekends_fires_sunday():
    alarm = make_alarm(time="09:00", repeat=REPEAT_WEEKENDS)
    sunday = datetime(2026, 9, 13, 9, 0)
    assert sunday.weekday() == 6
    assert is_due(alarm, sunday) is True


def test_snooze_fires_after_snooze_window_regardless_of_time_field():
    alarm = make_alarm(time="07:00", repeat=REPEAT_ONCE, snooze_minutes=5)
    now = datetime(2026, 9, 7, 7, 0)
    snooze(alarm, now)  # snoozed_until = 07:05
    just_before = now + timedelta(minutes=4, seconds=59)
    at_target = now + timedelta(minutes=5)
    assert is_due(alarm, just_before) is False
    assert is_due(alarm, at_target) is True


def test_dismiss_disables_one_shot_alarm():
    alarm = make_alarm(time="07:00", repeat=REPEAT_ONCE)
    now = datetime(2026, 9, 7, 7, 0)
    dismiss(alarm, now)
    assert alarm.enabled is False


def test_dismiss_keeps_recurring_alarm_enabled():
    alarm = make_alarm(time="07:00", repeat=REPEAT_DAILY)
    now = datetime(2026, 9, 7, 7, 0)
    dismiss(alarm, now)
    assert alarm.enabled is True


def test_next_occurrence_rolls_to_tomorrow_if_time_passed_today():
    alarm = make_alarm(time="07:00", repeat=REPEAT_DAILY)
    now = datetime(2026, 9, 7, 8, 0)  # already past 07:00 today
    nxt = next_occurrence(alarm, now)
    assert nxt.date() == (now.date() + timedelta(days=1))


def test_next_occurrence_none_when_disabled():
    alarm = make_alarm(time="07:00", enabled=False)
    now = datetime(2026, 9, 7, 6, 0)
    assert next_occurrence(alarm, now) is None
