# Pure scheduling logic, deliberately separated from I/O and the run loop.


from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Optional

from .models import Alarm, REPEAT_ONCE, REPEAT_DAILY, REPEAT_WEEKDAYS, REPEAT_WEEKENDS


def _day_matches(repeat: str, day: date) -> bool:
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


def is_due(alarm: Alarm, now: datetime) -> bool:
    """Whether alarm should fire at now (checked once per second).

    We compare now's HH:MM to the stored time, and use last_triggered_on to avoid
    re-firing every second for the full 60-second window that HH:MM covers.
    """
    if not alarm.enabled:
        return False

    # Snoozed alarms fire again at the snoozed time, ignoring the normal
    # HH:MM/repeat check entirely until the snooze resolves.
    if alarm.snoozed_until:
        snoozed_dt = datetime.fromisoformat(alarm.snoozed_until)
        return now >= snoozed_dt

    if not _day_matches(alarm.repeat, now.date()):
        return False

    current_hhmm = now.strftime("%H:%M")
    if current_hhmm != alarm.time:
        return False

    today_str = now.date().isoformat()
    if alarm.last_triggered_on == today_str:
        return False  # already fired today, don't refire within the same minute

    return True


def mark_triggered(alarm: Alarm, now: datetime) -> None:
    alarm.last_triggered_on = now.date().isoformat()
    alarm.snoozed_until = None


def snooze(alarm: Alarm, now: datetime) -> None:
    alarm.snoozed_until = (now + timedelta(minutes=alarm.snooze_minutes)).isoformat()


def dismiss(alarm: Alarm, now: datetime) -> None:
    """Dismiss without snoozing. One-shot alarms are disabled after firing
    so they don't clutter list output as if still pending."""
    mark_triggered(alarm, now)
    if alarm.repeat == REPEAT_ONCE:
        alarm.enabled = False


def next_occurrence(alarm: Alarm, now: datetime) -> Optional[datetime]:
    """Best-effort human-facing preview of when this alarm next fires.
    Not used for actual triggering (is_due is the source of truth) — only
    for the list command so users can see what's coming up."""
    if not alarm.enabled:
        return None
    if alarm.snoozed_until:
        return datetime.fromisoformat(alarm.snoozed_until)

    hour, minute = map(int, alarm.time.split(":"))
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)

    for _ in range(8):  # at most a week out, plenty for weekday/weekend modes
        if _day_matches(alarm.repeat, candidate.date()):
            return candidate
        candidate += timedelta(days=1)
    return None
