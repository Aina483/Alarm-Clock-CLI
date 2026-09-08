"""Scheduling logic and runtime polling loop."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, date
from typing import Optional

from .models import (
    Alarm,
    REPEAT_ONCE,
    REPEAT_DAILY,
    REPEAT_WEEKDAYS,
    REPEAT_WEEKENDS,
)
from .storage import AlarmStore
from .ringer import ring


def _day_matches(repeat: str, day: date) -> bool:
    """Return whether an alarm's recurrence allows the given day."""

    weekday = day.weekday()  # Monday=0 ... Sunday=6

    if repeat == REPEAT_DAILY:
        return True

    if repeat == REPEAT_WEEKDAYS:
        return weekday < 5

    if repeat == REPEAT_WEEKENDS:
        return weekday >= 5

    if repeat == REPEAT_ONCE:
        return True

    return False


def recurrence_matches_day(alarm: Alarm, day: date) -> bool:
    """
    Public wrapper around recurrence matching.

    ADDED: exposes the scheduling decision independently so it can
    be unit tested directly.
    """
    return _day_matches(alarm.repeat, day)


def _scheduled_datetime(alarm: Alarm, now: datetime) -> datetime:
    """
    Construct today's scheduled datetime for an alarm.
    """
    hour, minute = map(int, alarm.time.split(":"))

    return now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )


def is_due(alarm: Alarm, now: datetime) -> bool:
    """
    Determine whether an alarm should fire now.

    Priority:
        1. Disabled -> skip
        2. Snoozed -> only check snooze timestamp
        3. Recurrence -> check whether today is allowed
        4. Scheduled time -> now must be >= scheduled time
        5. Duplicate prevention -> don't fire twice today
    """

    
    if not alarm.enabled:
        return False

    
    # Snooze completely overrides the normal recurrence/time logic.
    if alarm.snoozed_until:
        snoozed_dt = datetime.fromisoformat(alarm.snoozed_until)
        return now >= snoozed_dt

    
    if not recurrence_matches_day(alarm, now.date()):
        return False

    
    scheduled = _scheduled_datetime(alarm, now)

    if now < scheduled:
        return False

    #prevent repeated firing on the same day.
    today_str = now.date().isoformat()

    if alarm.last_triggered_on == today_str:
        return False

    return True


def mark_triggered(alarm: Alarm, now: datetime) -> None:
    """Mark the alarm as having been handled today."""

    alarm.last_triggered_on = now.date().isoformat()
    alarm.snoozed_until = None


def snooze(alarm: Alarm, now: datetime) -> None:
    """Set an absolute timestamp for the next snooze firing."""

    alarm.snoozed_until = (
        now + timedelta(minutes=alarm.snooze_minutes)
    ).isoformat()


def dismiss(alarm: Alarm, now: datetime) -> None:
    """
    Dismiss the current alarm.

    One-shot alarms are disabled permanently after dismissal.
    Recurring alarms remain enabled.
    """

    mark_triggered(alarm, now)

    if alarm.repeat == REPEAT_ONCE:
        alarm.enabled = False


def next_occurrence(
    alarm: Alarm,
    now: datetime,
) -> Optional[datetime]:
    """
    Return the next expected occurrence for display.

    This is informational only. is_due() remains the source of truth
    for actual firing.
    """

    if not alarm.enabled:
        return None

    # Snooze takes priority.
    if alarm.snoozed_until:
        return datetime.fromisoformat(alarm.snoozed_until)

    hour, minute = map(int, alarm.time.split(":"))

    candidate = now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    if candidate <= now:
        candidate += timedelta(days=1)

    for _ in range(8):
        if recurrence_matches_day(alarm, candidate.date()):
            return candidate

        candidate += timedelta(days=1)

    return None


def _process_due_alarms(
    alarms: list[Alarm],
    now: datetime,
) -> bool:
    """
    Process all alarms that are currently due.

    Returns True if any alarm state changed and should be persisted.
    """

    changed = False

    for alarm in alarms:
        if not is_due(alarm, now):
            continue

        changed = True

        choice = ring(alarm)

        if choice == "snooze":
            snooze(alarm, now)
            print(
                f"Snoozed '{alarm.label}' "
                f"for {alarm.snooze_minutes}m."
            )
        else:
            dismiss(alarm, now)
            print(f"Dismissed '{alarm.label}'.")

    return changed


def run_loop(
    store: AlarmStore,
    interval: float = 1.0,
) -> None:
    """
    Run the foreground alarm scheduler.

    The scheduler polls periodically, but only reloads the JSON file
    when its modification time changes.

    This allows separate CLI invocations such as:

        alarm add ...
        alarm remove ...

    to affect an already-running scheduler process.
    """

    if interval <= 0:
        raise ValueError("Polling interval must be greater than 0.")

    print("Alarm clock running. Press Ctrl+C to stop.")

    #initial load.
    alarms = store.load()

    # remember the storage version currently in memory.
    cached_mtime = store.get_file_mtime()

    try:
        while True:
            # detect changes made by other CLI invocations.
            current_mtime = store.get_file_mtime()

            if current_mtime != cached_mtime:
                alarms = store.load()
                cached_mtime = current_mtime

            now = datetime.now()

            # scheduler owns orchestration instead of CLI.
            changed = _process_due_alarms(alarms, now)

            if changed:
                store.save(alarms)

                # update cached mtime after our own write.
                cached_mtime = store.get_file_mtime()

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopped.")