---
id: task-22
title: Design and implement meeting time tracking workflow
status: Done
assignee:
  - claude
created_date: '2026-02-25 15:25'
updated_date: '2026-02-25 15:30'
labels:
  - time-tracking
  - meetings
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define and implement how taskbridge handles meetings for time tracking purposes. Meetings come in two forms: ad-hoc (one-off, often created on the fly) and recurring (standing meetings that repeat on a schedule). Both need a frictionless path to start/stop time tracking without requiring a Todoist task to exist first, while still producing useful bartib entries that can be reported on.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ad-hoc meetings can be started quickly from the CLI with a description and optional project/client context
- [x] #2 Recurring meetings can be defined once and started by name or alias without re-entering details each time
- [x] #3 Meeting entries appear in bartib reports with a recognizable project name format (consistent with the Client::Project::tags encoding)
- [x] #4 Stopping a meeting session works the same as stopping any other tracked activity
- [x] #5 No Todoist task is required to track a meeting
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add `get_meetings`, `set_meeting`, `delete_meeting` to `Config` — recurring meeting definitions stored in `~/.taskbridge/config.yaml` under a `meetings` key as `{alias: {description, project, client, tags}}`
2. Add `meeting_app` typer subcommand group in `main.py` and register it as `taskbridge meeting`
3. Implement `meeting define <alias>` — save meeting definition to config
4. Implement `meeting list` — display defined meetings
5. Implement `meeting undefine <alias>` — remove a meeting definition
6. Implement `meeting start <name>` — resolve alias to definition (or treat as ad-hoc description), stop any active tracking, then start bartib using `build_bartib_project(project, client, tags)` with project defaulting to "meetings"; save DB record with synthetic `todoist_task_id = meeting:<slug>`
7. Write tests for the new config methods and the `build_bartib_project` usage pattern for meetings
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added a `meeting` subcommand group with four commands: `define`, `list`, `undefine`, and `start`.

Recurring meetings are stored in `~/.taskbridge/config.yaml` under a `meetings` key as `{alias: {description, project, client, tags}}`. Three new methods on `Config`: `get_meetings`, `set_meeting`, `delete_meeting`.

`meeting start <name>` resolves the name as an alias first; if not found, treats it as an ad-hoc description. CLI flags (`--project`, `--client`, `--tags`) override the stored definition. Project defaults to `"meetings"` when not specified. The bartib project is encoded with the existing `build_bartib_project()` function, e.g. `acme::webapp::standup,recurring`. A synthetic `todoist_task_id = "meeting:<slug>"` is written to the DB so `time stop` and `time list` work without any special-casing.

Stopping any previously active tracking is handled by the shared `stop_tracking_internal()` call, satisfying AC#4.

Modified files:
- `src/taskbridge/config.py` — `get_meetings`, `set_meeting`, `delete_meeting`
- `src/taskbridge/main.py` — `meeting_app` group + four commands
- `tests/unit/test_meetings.py` — 20 tests covering config methods and all CLI commands
<!-- SECTION:NOTES:END -->
