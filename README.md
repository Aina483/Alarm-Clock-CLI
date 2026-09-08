# Alarm Clock — Python CLI

A lightweight command-line alarm clock application built in Python.

The application allows users to create, view, remove, enable, disable, and run alarms directly from the terminal. Alarm state is persisted locally using a JSON file, with no database or external service.

---

## Requirements

### Functional Requirements

The application supports:

* Create an alarm with a time and optional label.
* List configured alarms.
* Remove an alarm.
* Enable or disable an alarm.
* Support multiple alarm recurrence modes:

  * `once`
  * `daily`
  * `weekdays`
  * `weekends`
* Run a background scheduler that continuously checks for due alarms.
* Trigger an alarm when its scheduled time is reached.
* Snooze an alarm for a configurable number of minutes.
* Dismiss an alarm.
* Persist alarm state between application runs.

### Technical Requirements

* Python CLI application.
* No web UI.
* No React or frontend framework.
* No database.
* Standard Python libraries are preferred where possible.
* Alarm data is persisted using a local JSON file.
* Core scheduling logic should be independently testable.
* CLI, scheduling, persistence, and notification responsibilities should remain separated.

---

## Design Scope

The application is intentionally designed as a small, modular CLI rather than a large framework-based application.

The main design goals are:

1. **Separation of concerns**
2. **Simple persistence**
3. **Testable business logic**
4. **Minimal dependencies**
5. **Clear CLI interface**
6. **Easy future extension**

### Project Structure

```text
Alarm_clock_python_cli/
│
├── alarm_clock/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── storage.py
│   ├── scheduler.py
│   ├── cli.py
│   └── ringer.py
│
├── tests/
│   ├── test_models.py
│   ├── test_storage.py
│   ├── test_scheduler.py
│   ├── test_cli.py
│   └── test_ringer.py
│
├── data/
│   └── alarms.json
│
├── pyproject.toml
├── uv.lock
├── README.md
└── .gitignore
```

---

# Architecture

The application is divided into several small components.

```text
                     ┌──────────────┐
                     │    main.py   │
                     │ Entry Point  │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │    cli.py    │
                     │ User Commands│
                     └──────┬───────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
       ┌──────────┐   ┌────────────┐  ┌──────────┐
       │ models.py│   │ scheduler  │  │ storage  │
       │  Alarm   │   │ Due Logic  │  │ JSON I/O │
       └──────────┘   └─────┬──────┘  └──────────┘
                             │
                             ▼
                       ┌──────────┐
                       │ ringer.py│
                       │ Notify   │
                       └──────────┘
```

### Responsibility of Each Module

#### `models.py`

Defines the `Alarm` domain model.

An alarm contains:

* ID
* Time
* Label
* Repeat mode
* Enabled/disabled state
* Snooze duration
* Last triggered date
* Snoozed-until timestamp

The model also provides serialization helpers for JSON persistence.

---

#### `storage.py`

Responsible only for persistence.

It:

* Loads alarms from the JSON file.
* Saves alarms to the JSON file.
* Creates the data file when necessary.
* Converts between `Alarm` objects and JSON-compatible dictionaries.

The storage layer does not decide whether an alarm is due.

---

#### `scheduler.py`

Contains the core alarm scheduling logic.

It determines:

* Whether an alarm is enabled.
* Whether its scheduled time has been reached.
* Whether the alarm has already fired for the current day.
* Whether its repeat pattern matches the current day.
* The next occurrence of an alarm.
* Snooze and dismissal state.

The scheduler is kept separate from the CLI so the scheduling rules can be tested independently.

---

#### `ringer.py`

Responsible for notifying the user when an alarm is triggered.

The scheduler decides:

```text
"Is this alarm due?"
```

The ringer decides:

```text
"How should the user be notified?"
```

This separation means the notification mechanism can be changed later without modifying scheduling logic.

---

#### `cli.py`

Provides the command-line interface using Python's built-in `argparse`.

It handles commands such as:

```text
add
list
remove
enable
disable
run
```

The CLI coordinates the other components but does not own their core business logic.

---

#### `main.py`

Acts as the application entry point.

It delegates execution to the CLI:

```python
from .cli import main


if __name__ == "__main__":
    main()
```

---

# Scheduler Design

The scheduler runs continuously when the application is started with:

```bash
uv run alarmclock run
```

The basic runtime flow is:

```text
Start application
       │
       ▼
Load alarms
       │
       ▼
Get current time
       │
       ▼
Check each alarm
       │
       ▼
Is alarm due?
   ┌───┴───┐
   │       │
  No      Yes
   │       │
   │       ▼
   │     Ringer
   │       │
   │       ▼
   │   Snooze/Dismiss
   │       │
   └───────┘
       │
       ▼
    Sleep
       │
       ▼
    Repeat
```

The scheduler checks the alarms once per second.

Keeping the check interval at one second provides sufficient precision for a CLI alarm clock while keeping the implementation simple.

---

## Recurrence

Four recurrence modes are supported.

### Once

The alarm fires once and is then considered completed.

```text
07:30 → Fire
Next day → Do not fire
```

### Daily

The alarm can fire every day at the configured time.

```text
Monday    → Fire
Tuesday   → Fire
Wednesday → Fire
...
```

### Weekdays

The alarm fires Monday through Friday.

```text
Monday    → Fire
Tuesday   → Fire
Wednesday → Fire
Thursday  → Fire
Friday    → Fire
Saturday  → No
Sunday    → No
```

### Weekends

The alarm fires Saturday and Sunday.

```text
Monday    → No
...
Friday    → No
Saturday  → Fire
Sunday    → Fire
```

---

# Preventing Duplicate Triggers

The scheduler keeps track of the date on which an alarm was last triggered.

For example:

```text
last_triggered_on = "2026-09-08"
```

This prevents the same alarm from firing repeatedly during the same minute/day while the scheduler continues running every second.

The alarm state is persisted so that runtime state is not lost unnecessarily between operations.

---

# Snooze

When an alarm is triggered, the user can choose to snooze or dismiss it.

For example:

```text
ALARM: Work is done

[s] Snooze
[d] Dismiss
```

If snoozed for five minutes:

```text
20:46 → Alarm
20:46 → Snooze
20:51 → Alarm again
```

The snooze duration is configurable when creating the alarm.

---

# Storage

Because the assessment does not allow a database, the application uses a JSON file for persistence.

The default storage location is:

```text
data/alarms.json
```

Example:

```json
[
  {
    "id": "a12b34cd",
    "time": "07:30",
    "label": "Wake up",
    "repeat": "daily",
    "enabled": true,
    "snooze_minutes": 5,
    "last_triggered_on": null,
    "snoozed_until": null
  }
]
```

### Why JSON?

JSON was selected because:

* It is part of Python's standard library.
* It requires no external service.
* It satisfies the no-database requirement.
* Alarm data is small enough that file-based persistence is sufficient.
* It is human-readable and easy to inspect during development.
* It keeps the implementation simple for a short build exercise.

For a production application with many users or concurrent writers, a database would be more appropriate.

---

# CLI Commands

The CLI executable is:

```bash
alarmclock
```

When using `uv`, commands can be executed with:

```bash
uv run alarmclock
```

## Show Help

```bash
uv run alarmclock --help
```

---

## Add an Alarm

```bash
uv run alarmclock add 07:30
```

With a label:

```bash
uv run alarmclock add 07:30 --label "Wake up"
```

With recurrence:

```bash
uv run alarmclock add 07:30 --label "Morning" --repeat daily
```

With a custom snooze duration:

```bash
uv run alarmclock add 07:30 --label "Morning" --snooze 10
```

Supported repeat values:

```text
once
daily
weekdays
weekends
```

---

## List Alarms

```bash
uv run alarmclock list
```

Example:

```text
ID        TIME    REPEAT    ENABLED  LABEL                NEXT
a12b34cd  07:30   daily     True     Wake up              2026-09-09 07:30
```

---

## Remove an Alarm

```bash
uv run alarmclock remove <alarm-id>
```

Example:

```bash
uv run alarmclock remove a12b34cd
```

---

## Enable an Alarm

```bash
uv run alarmclock enable <alarm-id>
```

---

## Disable an Alarm

```bash
uv run alarmclock disable <alarm-id>
```

---

## Run the Alarm Clock

```bash
uv run alarmclock run
```

Example:

```text
Alarm clock running. Press Ctrl+C to stop.
```

The process continuously checks the configured alarms.

Stop the scheduler with:

```text
Ctrl+C
```

---

# Testing

The project uses `pytest`.

Run the complete test suite:

```bash
uv run pytest
```

Run with more detailed output:

```bash
uv run pytest -v
```

Run a specific test module:

```bash
uv run pytest tests/test_models.py
```

```bash
uv run pytest tests/test_storage.py
```

```bash
uv run pytest tests/test_scheduler.py
```

```bash
uv run pytest tests/test_cli.py
```

---

# End-to-End Test

A simple manual end-to-end test can be performed by creating an alarm a minute or two in the future.

For example:

```bash
uv run alarmclock add 21:30 --label "Test Alarm"
```

Verify it:

```bash
uv run alarmclock list
```

Start the scheduler:

```bash
uv run alarmclock run
```

At the scheduled time, the application should trigger the ringer.

This validates the complete flow:

```text
CLI
 ↓
Alarm Model
 ↓
JSON Storage
 ↓
Scheduler
 ↓
Due Check
 ↓
Ringer
```

---

# Development Setup

The project uses `uv` for Python environment and dependency management.

Sync the environment:

```bash
uv sync
```

Run Python through the project environment:

```bash
uv run python
```

Run tests:

```bash
uv run pytest
```

Run the application:

```bash
uv run alarmclock
```

---

# Design Decisions

### Standard Library First

The implementation uses Python's standard library where practical:

* `argparse` — CLI parsing
* `json` — persistence format
* `pathlib` — filesystem handling
* `datetime` — time/date calculations
* `dataclasses` — alarm model
* `uuid` — alarm IDs
* `time` — scheduler loop

This minimizes dependencies and keeps the application portable.

### No Database

The assessment explicitly excludes database usage.

A JSON file provides sufficient persistence for the expected scale of the application.

### Pure Scheduling Logic

Scheduling decisions are separated from the infinite runtime loop.

This makes functions such as `is_due()` and `next_occurrence()` independently testable.

### Dependency Direction

The design keeps responsibilities flowing toward the domain rather than making every module depend on every other module.

```text
CLI
 │
 ├── Storage
 ├── Scheduler
 └── Domain Model

Scheduler
 │
 └── Domain Model

Storage
 │
 └── Domain Model

Ringer
 │
 └── Domain Model
```

---

# Known Limitations

This is intentionally a lightweight CLI application rather than a production-grade alarm service.

Current limitations include:

* The scheduler must remain running for alarms to trigger.
* Closing the terminal stops the scheduler.
* JSON storage is not designed for concurrent writes.
* There is no OS-level background service.
* Notification behavior is terminal-based.
* Timezone support is not explicitly modeled.
* There is no recurring custom schedule such as "every Monday and Wednesday."
* There is no authentication or multi-user support.
* The application does not synchronize alarms across machines.

These trade-offs keep the implementation appropriate for the scope of the assessment.

---

# Future Improvements

If this were expanded beyond the assessment, possible improvements would include:

* OS-native notifications.
* Cross-platform audio notification support.
* Background service/daemon support.
* Timezone-aware scheduling.
* More flexible recurrence rules.
* SQLite or PostgreSQL for persistent storage.
* Structured logging.
* Configuration management.
* Better concurrency handling.
* Packaging and distribution as an installable CLI.
* Integration tests for the complete scheduler lifecycle.

---

# Running the Application — Quick Reference

```bash
# Install/sync dependencies
uv sync

# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Show CLI help
uv run alarmclock --help

# Add alarm
uv run alarmclock add 07:30 --label "Wake up"

# Add daily alarm
uv run alarmclock add 07:30 --label "Morning" --repeat daily

# List alarms
uv run alarmclock list

# Remove alarm
uv run alarmclock remove <alarm-id>

# Enable alarm
uv run alarmclock enable <alarm-id>

# Disable alarm
uv run alarmclock disable <alarm-id>

# Start scheduler
uv run alarmclock run
```

---

## Summary

The application follows a modular architecture where each component has a focused responsibility:

```text
models.py
    ↓
Domain representation

storage.py
    ↓
Persistence

scheduler.py
    ↓
Scheduling decisions

ringer.py
    ↓
Alarm notification

cli.py
    ↓
User interaction

main.py
    ↓
Application entry point
```

The result is a small, testable, dependency-light alarm clock that satisfies the CLI-only and no-database constraints while leaving clear extension points for future functionality.
