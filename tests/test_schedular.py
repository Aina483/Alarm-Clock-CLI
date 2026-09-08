from datetime import datetime, timedelta
from unittest.mock import Mock

from alarm_clock.models import (
    Alarm,
    REPEAT_ONCE,
    REPEAT_DAILY,
    REPEAT_WEEKDAYS,
    REPEAT_WEEKENDS,
)
from alarm_clock.schedular import (
    is_due,
    mark_triggered,
    snooze,
    dismiss,
    next_occurrence,
    run_loop,
)


def make_alarm(**overrides):
    base = dict(
        id="abc123",
        time="07:00",
        label="Test",
        repeat=REPEAT_ONCE,
        snooze_minutes=5,
    )
    base.update(overrides)
    return Alarm(**base)


def test_fires_at_exact_time():
    alarm = make_alarm(time="07:00")
    now = datetime(2026, 9, 7, 7, 0)

    assert is_due(alarm, now) is True


# With >= semantics, an alarm should still fire if the scheduler
# misses the exact minute.
def test_fires_when_scheduler_checks_after_scheduled_time():
    alarm = make_alarm(time="07:00")
    now = datetime(2026, 9, 7, 7, 1)

    assert is_due(alarm, now) is True


def test_does_not_fire_before_scheduled_time():
    alarm = make_alarm(time="07:00")
    now = datetime(2026, 9, 7, 6, 59)

    assert is_due(alarm, now) is False


def test_disabled_alarm_never_due():
    alarm = make_alarm(
        time="07:00",
        enabled=False,
    )

    now = datetime(2026, 9, 7, 7, 0)

    assert is_due(alarm, now) is False


def test_does_not_refire_same_day_after_trigger():
    alarm = make_alarm(
        time="07:00",
        repeat=REPEAT_DAILY,
    )

    now = datetime(2026, 9, 7, 7, 0)

    assert is_due(alarm, now) is True

    mark_triggered(alarm, now)

    assert is_due(alarm, now) is False


def test_daily_fires_again_next_day():
    alarm = make_alarm(
        time="07:00",
        repeat=REPEAT_DAILY,
    )

    day1 = datetime(2026, 9, 7, 7, 0)
    mark_triggered(alarm, day1)

    day2 = datetime(2026, 9, 8, 7, 0)

    assert is_due(alarm, day2) is True


def test_weekdays_fires_on_monday():
    alarm = make_alarm(
        time="08:00",
        repeat=REPEAT_WEEKDAYS,
    )

    monday = datetime(2026, 9, 7, 8, 0)

    assert monday.weekday() == 0
    assert is_due(alarm, monday) is True


def test_weekdays_skips_saturday():
    alarm = make_alarm(
        time="08:00",
        repeat=REPEAT_WEEKDAYS,
    )

    saturday = datetime(2026, 9, 12, 8, 0)

    assert saturday.weekday() == 5
    assert is_due(alarm, saturday) is False


def test_weekends_fires_saturday():
    alarm = make_alarm(
        time="09:00",
        repeat=REPEAT_WEEKENDS,
    )

    saturday = datetime(2026, 9, 12, 9, 0)

    assert saturday.weekday() == 5
    assert is_due(alarm, saturday) is True


def test_weekends_fires_sunday():
    alarm = make_alarm(
        time="09:00",
        repeat=REPEAT_WEEKENDS,
    )

    sunday = datetime(2026, 9, 13, 9, 0)

    assert sunday.weekday() == 6
    assert is_due(alarm, sunday) is True


def test_once_alarm_can_fire_today():
    alarm = make_alarm(
        time="07:00",
        repeat=REPEAT_ONCE,
    )

    now = datetime(2026, 9, 7, 7, 0)

    assert is_due(alarm, now) is True


def test_snooze_fires_after_snooze_window_regardless_of_time_field():
    alarm = make_alarm(
        time="07:00",
        repeat=REPEAT_ONCE,
        snooze_minutes=5,
    )

    now = datetime(2026, 9, 7, 7, 0)

    snooze(alarm, now)

    just_before = now + timedelta(
        minutes=4,
        seconds=59,
    )

    at_target = now + timedelta(minutes=5)

    assert is_due(alarm, just_before) is False
    assert is_due(alarm, at_target) is True


# Snooze must take priority over normal recurrence.
def test_snooze_ignores_recurrence():
    alarm = make_alarm(
        time="07:00",
        repeat=REPEAT_WEEKDAYS,
        snooze_minutes=5,
    )

    friday = datetime(2026, 9, 11, 23, 58)

    snooze(alarm, friday)

    saturday = datetime(2026, 9, 12, 0, 3)

    # Saturday is not a weekday, but the snooze should still fire.
    assert saturday.weekday() == 5
    assert is_due(alarm, saturday) is True


# Disabled must win over snooze.
def test_disabled_alarm_with_snooze_is_not_due():
    alarm = make_alarm(
        enabled=False,
        snoozed_until="2026-09-07T07:05:00",
    )

    now = datetime(2026, 9, 7, 7, 5)

    assert is_due(alarm, now) is False


def test_snooze_crossing_midnight():
    alarm = make_alarm(
        time="23:59",
        snooze_minutes=5,
    )

    start = datetime(2026, 9, 7, 23, 59)

    snooze(alarm, start)

    after_midnight = datetime(2026, 9, 8, 0, 4)

    assert is_due(alarm, after_midnight) is True


def test_dismiss_disables_one_shot_alarm():
    alarm = make_alarm(
        time="07:00",
        repeat=REPEAT_ONCE,
    )

    now = datetime(2026, 9, 7, 7, 0)

    dismiss(alarm, now)

    assert alarm.enabled is False
    assert alarm.last_triggered_on == "2026-09-07"
    assert alarm.snoozed_until is None


def test_dismiss_keeps_recurring_alarm_enabled():
    alarm = make_alarm(
        time="07:00",
        repeat=REPEAT_DAILY,
    )

    now = datetime(2026, 9, 7, 7, 0)

    dismiss(alarm, now)

    assert alarm.enabled is True
    assert alarm.last_triggered_on == "2026-09-07"


def test_snooze_sets_absolute_timestamp():
    alarm = make_alarm(snooze_minutes=5)

    now = datetime(2026, 9, 7, 7, 0)

    snooze(alarm, now)

    assert alarm.snoozed_until == "2026-09-07T07:05:00"


def test_next_occurrence_rolls_to_tomorrow_if_time_passed_today():
    alarm = make_alarm(
        time="07:00",
        repeat=REPEAT_DAILY,
    )

    now = datetime(2026, 9, 7, 8, 0)

    nxt = next_occurrence(alarm, now)

    assert nxt.date() == (
        now.date() + timedelta(days=1)
    )


def test_next_occurrence_returns_snooze_time():
    alarm = make_alarm(
        snoozed_until="2026-09-07T07:05:00",
    )

    now = datetime(2026, 9, 7, 7, 0)

    nxt = next_occurrence(alarm, now)

    assert nxt == datetime(2026, 9, 7, 7, 5)


def test_next_occurrence_none_when_disabled():
    alarm = make_alarm(
        time="07:00",
        enabled=False,
    )

    now = datetime(2026, 9, 7, 6, 0)

    assert next_occurrence(alarm, now) is None



# Validate the mtime cache independently from real sleeping.
def test_run_loop_reloads_alarms_when_file_mtime_changes(monkeypatch):
    alarm = make_alarm(
        time="07:00",
        repeat=REPEAT_DAILY,
    )

    store = Mock()

    store.load.side_effect = [
        [alarm],
        [alarm],
    ]

    store.get_file_mtime.side_effect = [
        1.0,  # initial
        1.0,  # first poll
        2.0,  # file changed
        2.0,  # after reload
    ]

    # Stop after the second iteration.
    sleep_calls = 0

    def fake_sleep(_):
        nonlocal sleep_calls
        sleep_calls += 1

        if sleep_calls >= 2:
            raise KeyboardInterrupt

    monkeypatch.setattr(
        "alarm_clock.schedular.time.sleep",
        fake_sleep,
    )

    # Never actually ring anything.
    monkeypatch.setattr(
        "alarm_clock.schedular._process_due_alarms",
        lambda alarms, now: False,
    )

    run_loop(store, interval=1)

    # Initial load + reload after mtime changed.
    assert store.load.call_count == 2


def test_run_loop_rejects_non_positive_interval():
    store = Mock()

    try:
        run_loop(store, interval=0)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "greater than 0" in str(exc)