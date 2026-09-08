"""Handles what happens when an alarm fires: terminal bell + prompt.

Ringing is terminal-only (ASCII bell '\\a' + a visible banner), no audio library dependency. 
This keeps the project dependency-free. The bell char is beeped on its own background thread so the alarm
keeps audibly nagging while we block on input() for dismiss/snooze.
"""
from __future__ import annotations

import sys
import threading
import time

from .models import Alarm


def _beep_loop(stop_event: threading.Event, interval: float = 1.0) -> None:
    while not stop_event.is_set():
        sys.stdout.write("\a")
        sys.stdout.flush()
        stop_event.wait(interval)


def ring(alarm: Alarm) -> str:
    """Blocks until the user dismisses or snoozes. Returns snooze or
    dismiss."""
    banner = f"\n{'=' * 40}\n  ALARM: {alarm.label}  ({alarm.time})\n{'=' * 40}"
    print(banner)

    stop_event = threading.Event()
    beeper = threading.Thread(target=_beep_loop, args=(stop_event,), daemon=True)
    beeper.start()

    try:
        while True:
            choice = input(
                f"[Enter] dismiss   [s] snooze {alarm.snooze_minutes}m   > "
            ).strip().lower()
            if choice in ("", "d", "dismiss"):
                return "dismiss"
            if choice in ("s", "snooze"):
                return "snooze"
            print("Please press Enter to dismiss, or 's' to snooze.")
    finally:
        stop_event.set()
        beeper.join(timeout=2)
