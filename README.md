# Alarm Clock — Python CLI

A lightweight command-line alarm clock built in Python as part of a time-boxed software engineering assessment.

The application supports alarm creation, recurrence, snoozing, dismissal, enable/disable controls, JSON persistence, and a foreground scheduler loop.

The implementation intentionally uses the Python standard library for the application itself, with `pytest` used for testing.

---

## 1. Requirements

### Functional Requirements

The application supports:

* Add an alarm
* List alarms
* Remove an alarm
* Enable an alarm
* Disable an alarm
* Run the alarm clock
* Snooze a ringing alarm
* Dismiss a ringing alarm
* Recurring alarms:

  * `once`
  * `daily`
  * `weekdays`
  * `weekends`
* Persistent alarm state across application restarts

### Non-Functional Requirements

* CLI only
* No web UI
* No database
* Foreground process
* JSON-based persistence
* Approximately one-second scheduler polling interval
* Clear separation between domain logic, persistence, scheduling, and presentation
* Automated tests for core behavior

---

## 2. Scope

### Included

* Multiple alarms
* Unique alarm IDs
* Alarm labels
* Recurrence
* Snooze
* Enable/disable
* Persistent state
* Runtime alarm detection
* Terminal-based alarm notification
* CLI validation
* Automated tests

### Out of Scope

The following were intentionally excluded to keep the implementation focused:

* Web or graphical UI
* Database persistence
* Background daemon/service
* Multi-user support
* Timezone management
* DST-specific behavior
* Arbitrary weekday combinations
* Concurrent writers/file locking
* In-place alarm editing
* Distributed scheduling

---

## 3. Architecture

The application is split into small components with clear responsibilities:

```text
alarm_clock/
│
├── main.py
├── cli.py
├── models.py
├── storage.py
├── schedular.py
└── ringer.py
```

### Responsibility of Each Module

#### `models.py`

Defines the `Alarm` domain model.

Responsible for:

* Alarm state
* Alarm creation
* Serialization/deserialization

The model is intentionally dependency-light and uses a dataclass.

---

#### `storage.py`

Responsible only for JSON persistence.

Responsibilities:

* Load alarms
* Save alarms
* Handle missing storage files
* Detect corrupted storage
* Expose file modification time for runtime change detection

Storage has no knowledge of:

* recurrence
* due dates
* snoozing
* ringing
* CLI behavior

This keeps persistence independent from scheduling.

---

#### `schedular.py`

Contains the core scheduling logic.

Responsibilities:

* Determine whether an alarm is due
* Evaluate recurrence rules
* Handle snooze state
* Prevent duplicate firing
* Calculate the next occurrence
* Run the foreground scheduler loop
* Reload persisted state when the storage file changes

This is the main business-logic layer of the application.

---

#### `ringer.py`

Handles the interaction that occurs when an alarm fires.

Responsibilities:

* Display the alarm
* Produce a terminal bell
* Wait for user interaction
* Return either `dismiss` or `snooze`

The ringer does not modify alarm persistence or make scheduling decisions.

---

#### `cli.py`

Responsible for:

* Argument parsing
* Input validation
* Command dispatch
* User-facing error messages

The CLI delegates business logic to the appropriate modules instead of implementing scheduling itself.

---

#### `main.py`

Thin application entry point.

It simply delegates execution to the CLI.

---

## 4. Dependency Direction

The project follows a one-way dependency flow:

```text
models
   ↓
storage / ringer
   ↓
scheduler
   ↓
cli
   ↓
main
```

The intention is to avoid circular dependencies and keep individual components independently testable.

---

# 5. Scheduling Design

The scheduler is the most important part of the application.

## Polling Strategy

The alarm clock runs as a foreground process and checks for due alarms approximately once per second.

```text
Start
  ↓
Load alarms
  ↓
Check storage modification time
  ↓
Reload if external changes detected
  ↓
Get current time
  ↓
Evaluate alarms
  ↓
Ring due alarms
  ↓
Persist changed state
  ↓
Sleep
  ↓
Repeat
```

### Why Polling?

For a small CLI application, polling provides a simple and predictable solution.

More complicated approaches such as:

* `threading.Timer`
* Python's `sched`
* OS-specific file watchers
* background workers

would introduce additional complexity without providing meaningful benefits for this assessment.

---

## External Changes and File Modification Time

The scheduler may be running continuously while another CLI command modifies the alarms.

For example:

```text
Terminal 1:
uv run alarmclock run

Terminal 2:
uv run alarmclock disable abc123
```

The running scheduler therefore needs to notice that the persisted state has changed.

Instead of reading the JSON file every second, the scheduler tracks the file's modification time.

```text
File unchanged
    ↓
Keep in-memory alarms

File changed
    ↓
Reload alarms from JSON
```

This provides cross-process state refresh while avoiding unnecessary disk reads.

---

# 6. Alarm Due Logic

The scheduler evaluates an alarm through a small set of rules.

### 1. Disabled alarms

A disabled alarm is never due.

### 2. Snoozed alarms

If an alarm is snoozed, the snooze timestamp takes priority over its normal recurrence schedule.

```text
snoozed_until != None
        ↓
now >= snoozed_until
        ↓
fire
```

This means a snoozed alarm is not accidentally blocked by its normal scheduled time.

### 3. Recurrence

The scheduler checks whether the current day is valid for the alarm:

```text
once       → valid according to one-shot state
daily      → every day
weekdays   → Monday-Friday
weekends   → Saturday-Sunday
```

### 4. Scheduled time

The scheduler uses a `now >= scheduled_time` comparison rather than requiring an exact clock match.

This allows the system to recover from a delayed scheduler tick.

For example:

```text
Alarm: 07:00

Scheduler checks at:
07:00:00 → due
07:00:01 → still potentially due
07:00:05 → still potentially due
```

`last_triggered_on` prevents the alarm from firing repeatedly.

### 5. Duplicate prevention

After an alarm fires, its `last_triggered_on` value is updated.

This prevents repeated firing during the same scheduled window.

---

# 7. Snooze Design

Snooze is represented using an absolute timestamp:

```text
snoozed_until = current_time + snooze_duration
```

For example:

```text
Alarm rings at 07:00
Snooze duration = 5 minutes

snoozed_until = 07:05
```

The scheduler then checks:

```text
now >= snoozed_until
```

Using an absolute timestamp is preferable to maintaining a decrementing counter because it naturally handles delays and crossing midnight.

For example:

```text
23:58 + 5 minutes
       ↓
00:03
```

No special midnight logic is required.

---

# 8. Alarm Lifecycle

For a one-time alarm:

```text
Enabled
   ↓
Due
   ↓
Ring
   ↓
Dismiss
   ↓
Disabled
```

For a recurring alarm:

```text
Enabled
   ↓
Due
   ↓
Ring
   ↓
Dismiss
   ↓
Remain enabled
   ↓
Next occurrence
```

For snooze:

```text
Due
 ↓
Ring
 ↓
Snooze
 ↓
snoozed_until
 ↓
Ring again
 ↓
Dismiss / Snooze
```

---

# 9. Persistence

Alarm state is persisted as JSON.

Example:

```json
[
  {
    "id": "a12bc345",
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

### Storage behavior

#### Missing file

If the storage file does not exist:

```text
load() → []
```

The application does not create a file simply because it was read.

The file and parent directory are created when the first alarm is saved.

#### Corrupted JSON

Corrupted JSON is treated as an error rather than silently resetting the application to an empty alarm list.

This avoids hiding potential data-loss conditions.

---

# 10. CLI

The application exposes the following commands:

```bash
alarmclock add <HH:MM> [--label TEXT] [--repeat MODE] [--snooze MINUTES]

alarmclock list

alarmclock list --all

alarmclock remove <ID>

alarmclock enable <ID>

alarmclock disable <ID>

alarmclock run [--interval SECONDS]
```

### Examples

Add a one-time alarm:

```bash
uv run alarmclock add 07:30 --label "Wake up"
```

Add a daily alarm:

```bash
uv run alarmclock add 08:00 --label "Standup" --repeat daily
```

Add a weekday alarm:

```bash
uv run alarmclock add 09:00 --label "Work" --repeat weekdays
```

Add a weekend alarm:

```bash
uv run alarmclock add 10:00 --label "Weekend" --repeat weekends
```

List alarms:

```bash
uv run alarmclock list
```

Disable an alarm:

```bash
uv run alarmclock disable a12bc345
```

Enable it again:

```bash
uv run alarmclock enable a12bc345
```

Remove an alarm:

```bash
uv run alarmclock remove a12bc345
```

Start the scheduler:

```bash
uv run alarmclock run
```

Use a custom polling interval:

```bash
uv run alarmclock run --interval 2
```

---

# 11. Terminal Alarm Interaction

When an alarm fires, the application displays a terminal notification:

```text
========================================
  ALARM: Wake up  (07:30)
========================================

[Enter] dismiss   [s] snooze 5m   >
```

The terminal bell is emitted repeatedly while waiting for user input.

Supported actions:

```text
Enter / d / dismiss → dismiss
s / snooze          → snooze
```

The ringing implementation uses a background thread and `threading.Event` so the terminal can continue producing the bell while the main thread waits for input.

---

# 12. Testing

The project uses `pytest`.

Run the test suite with:

```bash
uv run pytest
```

The tests focus particularly on scheduling behavior because that is the most error-prone part of the application.

Coverage includes:

### Scheduling

* Alarm fires at scheduled time
* Alarm does not fire when disabled
* Duplicate firing prevention
* Daily recurrence
* Weekday recurrence
* Weekend recurrence
* Snooze behavior
* Snooze crossing time boundaries
* One-shot dismissal
* Recurring alarm dismissal
* Next occurrence calculation

### Storage

* Save/load round trip
* Missing file behavior
* Corrupted JSON handling
* Parent directory creation

### CLI

* Valid time parsing
* Single-digit hour normalization
* Midnight
* `23:59`
* Invalid time rejection

### Ringer

The ringer interaction is isolated so it can be tested independently from scheduling and persistence.

---

# 13. Error Handling

Expected user errors are handled at the CLI boundary.

Examples include:

* Invalid time format
* Invalid repeat mode
* Invalid snooze duration
* Unknown alarm ID
* Invalid polling interval
* Corrupted alarm storage

The application should provide a clear error message rather than exposing an unnecessary Python traceback for normal user mistakes.

---

# 14. Engineering Decisions

## Why JSON instead of a database?

The requirements explicitly exclude a database.

The expected alarm count is small, so reading and rewriting a single JSON document is sufficient.

Introducing SQLite or another database would add unnecessary complexity.

---

## Why polling instead of `threading.Timer`?

The application needs to support multiple alarms and state changes coming from separate CLI invocations.

A centralized polling loop makes it easier to:

* detect newly added alarms
* detect disabled/removed alarms
* handle recurrence
* handle snooze
* recover from delayed scheduler ticks

---

## Why use `last_triggered_on`?

Because the scheduler checks frequently.

Without duplicate protection, an alarm scheduled for `07:00` could potentially fire multiple times while the current time remains inside the `07:00` minute.

`last_triggered_on` makes firing idempotent for a given day.

---

## Why store `snoozed_until` as a timestamp?

An absolute timestamp is simpler and more robust than maintaining a countdown.

It also naturally handles:

* scheduler delays
* midnight
* different polling intervals

---

## Why separate the ringer?

The scheduler should decide **when** an alarm is due.

The ringer should decide **how the user interacts with it**.

This separation makes the scheduling logic testable without requiring terminal input.

---

# 15. Commit Strategy

Implementation was developed incrementally through focused commits.

The progression was:

```text
chore: initialize alarm clock project
feat: add alarm domain model
feat: add alarm persistence
feat: implement alarm scheduling logic
feat: add command line interface
feat: add application entry point
feat: add alarm runtime loop
feat: handle alarm lifecycle and recurrence
fix: improve CLI validation and error handling
docs: add project documentation
```

The intent was to keep each commit focused on one logical change rather than combining unrelated functionality.

---

# 16. Code Quality Principles

The implementation prioritizes:

### Separation of concerns

Each module has a single primary responsibility.

### Small functions

Scheduling rules are broken into focused functions such as:

```python
is_due()
snooze()
dismiss()
next_occurrence()
```

### Minimal dependencies

The application itself relies on the Python standard library.

### Testability

The scheduler is largely deterministic because it receives the current time as an argument.

This makes edge cases straightforward to test without depending on the actual system clock.

### Explicit state

Alarm lifecycle state such as:

```text
enabled
last_triggered_on
snoozed_until
```

is stored explicitly rather than inferred from side effects.

### Defensive validation

User-facing inputs are validated at the CLI boundary.

---

# 17. Limitations

This implementation is intentionally scoped for a small single-user CLI application.

Known limitations include:

* No timezone/DST support
* No concurrent file locking
* JSON is not suitable for very large alarm datasets
* Terminal bell behavior depends on the terminal/OS configuration
* No background daemon
* Only predefined recurrence modes are supported
* No web or graphical interface
* No audio file playback
* File-based persistence assumes a single logical writer

These limitations are deliberate rather than accidental scope expansion.

---

# 18. Running the Project

Install dependencies:

```bash
uv sync
```

Run the CLI:

```bash
uv run alarmclock --help
```

Run tests:

```bash
uv run pytest
```

Start the alarm clock:

```bash
uv run alarmclock run
```

---

# 19. Example End-to-End Flow

```text
$ uv run alarmclock add 20:46 --label "Work is done"

Added alarm 8f31c2a1: 20:46 (once) 'Work is done'
```

Then:

```text
$ uv run alarmclock list

ID        TIME    REPEAT    ENABLED  LABEL               NEXT
8f31c2a1  20:46   once      True     Work is done        2026-09-09 20:46
```

Start the scheduler:

```text
$ uv run alarmclock run

Alarm clock running. Press Ctrl+C to stop.

========================================
  ALARM: Work is done  (20:46)
========================================

[Enter] dismiss   [s] snooze 5m   >
```

Pressing Enter dismisses the alarm.

For a one-time alarm, it becomes disabled after dismissal.

---

# 20. Summary

This project intentionally favors **simple, explicit engineering over unnecessary complexity**.

The core design consists of:

```text
Dataclass
    ↓
JSON Persistence
    ↓
Polling Scheduler
    ↓
Recurrence + Snooze State
    ↓
Terminal Ringer
    ↓
CLI
```

The most important design considerations were:

* Clear separation of responsibilities
* Cross-process persistence awareness
* Robust due-time detection
* Explicit alarm lifecycle state
* Snooze handling using absolute timestamps
* Duplicate-fire prevention
* Automated testing of scheduling edge cases
* Minimal dependencies
* Deliberately constrained scope
