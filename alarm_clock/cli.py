"""Command-line interface: argument parsing + command dispatch.
Zero extra dependency, and the command surface here (add/list/remove/enable/disable/run) is small
enough that argparse's extra verbosity doesn't cost much.
"""
from __future__ import annotations

import argparse
import re
import sys
import time as time_module
from datetime import datetime

from .models import Alarm, VALID_REPEATS, REPEAT_ONCE
from .storage import AlarmStore
from .schedular import is_due, next_occurrence, snooze, dismiss
from .ringer import ring

TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def parse_time(value: str) -> str:
    if not TIME_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a valid 24-hour time. Use HH:MM, e.g. 07:30 or 22:00."
        )
    hour, minute = value.split(":")
    return f"{int(hour):02d}:{minute}"  # normalize e.g. "7:30" -> "07:30"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alarmclock", description="A simple CLI alarm clock.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a new alarm")
    p_add.add_argument("time", type=parse_time, help="Time in 24-hour HH:MM format")
    p_add.add_argument("--label", default="Alarm", help="Name/label for the alarm")
    p_add.add_argument(
        "--repeat", choices=sorted(VALID_REPEATS), default=REPEAT_ONCE,
        help="Repeat schedule (default: once)",
    )
    p_add.add_argument(
        "--snooze", type=int, default=5, metavar="MIN",
        help="Snooze duration in minutes (default: 5)",
    )

    sub.add_parser("list", help="List all alarms")

    p_remove = sub.add_parser("remove", help="Remove an alarm by id")
    p_remove.add_argument("id")

    p_enable = sub.add_parser("enable", help="Enable an alarm by id")
    p_enable.add_argument("id")

    p_disable = sub.add_parser("disable", help="Disable an alarm by id")
    p_disable.add_argument("id")

    sub.add_parser("run", help="Start the alarm clock (blocks, checks every second)")

    return parser


def cmd_add(args, store: AlarmStore) -> None:
    alarms = store.load()
    alarm = Alarm.new(args.time, args.label, args.repeat, args.snooze)
    alarms.append(alarm)
    store.save(alarms)
    print(f"Added alarm {alarm.id}: {alarm.time} ({alarm.repeat}) '{alarm.label}'")


def cmd_list(args, store: AlarmStore) -> None:
    alarms = store.load()
    if not alarms:
        print("No alarms set.")
        return
    now = datetime.now()
    print(f"{'ID':<10}{'TIME':<8}{'REPEAT':<10}{'ENABLED':<9}{'LABEL':<20}{'NEXT'}")
    for a in alarms:
        nxt = next_occurrence(a, now)
        nxt_str = nxt.strftime("%Y-%m-%d %H:%M") if nxt else "-"
        print(
            f"{a.id:<10}{a.time:<8}{a.repeat:<10}{str(a.enabled):<9}{a.label:<20}{nxt_str}"
        )


def _find(alarms, alarm_id):
    for a in alarms:
        if a.id == alarm_id:
            return a
    return None


def cmd_remove(args, store: AlarmStore) -> None:
    alarms = store.load()
    alarm = _find(alarms, args.id)
    if not alarm:
        print(f"No alarm with id {args.id}")
        sys.exit(1)
    alarms.remove(alarm)
    store.save(alarms)
    print(f"Removed alarm {args.id}")


def _set_enabled(args, store: AlarmStore, enabled: bool) -> None:
    alarms = store.load()
    alarm = _find(alarms, args.id)
    if not alarm:
        print(f"No alarm with id {args.id}")
        sys.exit(1)
    alarm.enabled = enabled
    store.save(alarms)
    print(f"{'Enabled' if enabled else 'Disabled'} alarm {args.id}")


def cmd_run(args, store: AlarmStore) -> None:
    print("Alarm clock running. Press Ctrl+C to stop.")
    try:
        while True:
            alarms = store.load()
            now = datetime.now()
            fired = False
            for alarm in alarms:
                if is_due(alarm, now):
                    fired = True
                    choice = ring(alarm)
                    if choice == "snooze":
                        snooze(alarm, now)
                        print(f"Snoozed '{alarm.label}' for {alarm.snooze_minutes}m.")
                    else:
                        dismiss(alarm, now)
                        print(f"Dismissed '{alarm.label}'.")
            if fired:
                store.save(alarms)
            time_module.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = AlarmStore()

    dispatch = {
        "add": cmd_add,
        "list": cmd_list,
        "remove": cmd_remove,
        "enable": lambda a, s: _set_enabled(a, s, True),
        "disable": lambda a, s: _set_enabled(a, s, False),
        "run": cmd_run,
    }
    dispatch[args.command](args, store)


if __name__ == "__main__":
    main()
