"""Command-line interface: argument parsing + command dispatch."""

from __future__ import annotations

import argparse
import re
import sys

from .models import Alarm, VALID_REPEATS, REPEAT_ONCE
from .storage import AlarmStore
from .schedular import next_occurrence, run_loop


TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def parse_time(value: str) -> str:
    if not TIME_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a valid 24-hour time. "
            "Use HH:MM, e.g. 07:30 or 22:00."
        )

    hour, minute = value.split(":")

    return f"{int(hour):02d}:{minute}"


def positive_float(value: str) -> float:
    """Validate positive numeric CLI arguments."""

    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a valid number."
        ) from exc

    if number <= 0:
        raise argparse.ArgumentTypeError(
            "Value must be greater than 0."
        )

    return number


def positive_int(value: str) -> int:
    """Validate positive integer CLI arguments."""

    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a valid integer."
        ) from exc

    if number <= 0:
        raise argparse.ArgumentTypeError(
            "Value must be greater than 0."
        )

    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alarmclock",
        description="A simple CLI alarm clock.",
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # Add

    p_add = sub.add_parser(
        "add",
        help="Add a new alarm",
    )

    p_add.add_argument(
        "time",
        type=parse_time,
        help="Time in 24-hour HH:MM format",
    )

    p_add.add_argument(
        "--label",
        default="Alarm",
        help="Name/label for the alarm",
    )

    p_add.add_argument(
        "--repeat",
        choices=sorted(VALID_REPEATS),
        default=REPEAT_ONCE,
        help="Repeat schedule (default: once)",
    )

    p_add.add_argument(
        "--snooze",
        type=positive_int,
        default=5,
        metavar="MIN",
        help="Snooze duration in minutes (default: 5)",
    )

    # list

    p_list = sub.add_parser(
        "list",
        help="List alarms",
    )

    #show disabled alarms only when explicitly requested.
    p_list.add_argument(
        "--all",
        action="store_true",
        help="Include disabled alarms",
    )

    # remove

    p_remove = sub.add_parser(
        "remove",
        help="Remove an alarm by id",
    )

    p_remove.add_argument("id")

    # enable

    p_enable = sub.add_parser(
        "enable",
        help="Enable an alarm by id",
    )

    p_enable.add_argument("id")

    # disable

    p_disable = sub.add_parser(
        "disable",
        help="Disable an alarm by id",
    )

    p_disable.add_argument("id")

    # run

    p_run = sub.add_parser(
        "run",
        help="Start the alarm clock",
    )

    #configurable polling resolution.
    p_run.add_argument(
        "--interval",
        type=positive_float,
        default=1.0,
        metavar="SECONDS",
        help="Polling interval in seconds (default: 1)",
    )

    return parser


def cmd_add(args, store: AlarmStore) -> None:
    alarms = store.load()

    alarm = Alarm.new(
        args.time,
        args.label,
        args.repeat,
        args.snooze,
    )

    alarms.append(alarm)

    store.save(alarms)

    print(
        f"Added alarm {alarm.id}: "
        f"{alarm.time} ({alarm.repeat}) '{alarm.label}'"
    )


def cmd_list(args, store: AlarmStore) -> None:
    alarms = store.load()

    #hide disabled alarms unless --all is supplied.
    if not args.all:
        alarms = [alarm for alarm in alarms if alarm.enabled]

    if not alarms:
        print("No alarms set.")
        return

    from datetime import datetime

    now = datetime.now()

    print(
        f"{'ID':<10}"
        f"{'TIME':<8}"
        f"{'REPEAT':<10}"
        f"{'ENABLED':<9}"
        f"{'LABEL':<20}"
        f"{'NEXT'}"
    )

    for alarm in alarms:
        nxt = next_occurrence(alarm, now)

        nxt_str = (
            nxt.strftime("%Y-%m-%d %H:%M")
            if nxt
            else "-"
        )

        print(
            f"{alarm.id:<10}"
            f"{alarm.time:<8}"
            f"{alarm.repeat:<10}"
            f"{str(alarm.enabled):<9}"
            f"{alarm.label:<20}"
            f"{nxt_str}"
        )


def _find(alarms, alarm_id):
    for alarm in alarms:
        if alarm.id == alarm_id:
            return alarm

    return None


def cmd_remove(args, store: AlarmStore) -> None:
    alarms = store.load()

    alarm = _find(alarms, args.id)

    if not alarm:
        # CHANGED: expected errors go to stderr.
        print(
            f"Error: no alarm with id {args.id}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    alarms.remove(alarm)

    store.save(alarms)

    print(f"Removed alarm {args.id}")


def _set_enabled(
    args,
    store: AlarmStore,
    enabled: bool,
) -> None:
    alarms = store.load()

    alarm = _find(alarms, args.id)

    if not alarm:
        #expected errors go to stderr.
        print(
            f"Error: no alarm with id {args.id}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    alarm.enabled = enabled

    # Optional state cleanup when explicitly disabling.
    if not enabled:
        alarm.snoozed_until = None

    store.save(alarms)

    print(
        f"{'Enabled' if enabled else 'Disabled'} "
        f"alarm {args.id}"
    )


def cmd_run(args, store: AlarmStore) -> None:
    # CLI no longer owns the scheduler loop.
    # It only delegates to the scheduler.
    run_loop(
        store,
        interval=args.interval,
    )


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

    try:
        dispatch[args.command](args, store)

    except (ValueError, RuntimeError) as exc:
        #clean expected application errors.
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()