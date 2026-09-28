---
id: TASK-42
title: Add note open/create button to web UI activity edit modal
status: Done
assignee:
  - '@iross'
created_date: '2026-09-02 14:56'
updated_date: '2026-09-02 15:00'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Past bartib activities linked to a Todoist task have no way to jump to that task's Obsidian note from the web UI — only the currently-tracked task's card has an Open/Create Note button. Extending that capability to the activity edit modal lets a user reach a task's note from its history entry, not just while actively tracking it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Activity edit modal shows a Note button when the entry's bartib start time matches a task_time_tracking record with a real Todoist task id (not a meeting: or cal: placeholder)
- [x] #2 Clicking Note opens the existing mapped note if one exists, or creates it (and its Todoist mapping) and then opens it, mirroring the currently-tracked card's behavior
- [x] #3 No Note button appears for entries with no linked Todoist task, or for meeting/calendar entries
- [x] #4 Creating a note from the edit modal does not require the entry's task to be the one currently being tracked
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add Database.get_tracking_in_range()-based helper in web_ui.py that maps minute-precision started_at -> todoist_task_id, to join bartib's plain-text activity rows (parsed at minute precision) back to the task_time_tracking records created at start time.
2. Extend _read_activities() to attach todoist_task_id and note_url (via a single get_all_todoist_mappings() lookup) to each activity dict, excluding meeting:/cal: placeholder ids.
3. Extract the existing active-tracking note create/lookup logic in _handle_note_create into a shared _get_or_create_task_note(task_id) helper; add a new POST /api/activity/note endpoint that calls it for an arbitrary todoist_task_id from the request body.
4. In the edit modal JS, render a Note button (open existing or create) when the activity has a todoist_task_id, reusing the existing openNote() helper and adding a small createActivityNote() for the create path.
5. Unit tests for the new pure-Python helpers (task id/time join, note get-or-create) with mocked db/TodoistAPI.
6. Manual check with the web UI that history entries with a linked task show the button and open/create the note correctly.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Extracted the note get-or-create logic that previously lived only in _handle_note_create into a module-level _get_or_create_task_note(task_id), so it works for any Todoist task id, not just the currently-tracked one. The active-tracking endpoint now delegates to it unchanged; a new POST /api/activity/note endpoint calls it for a task id supplied in the request body, rejecting empty/meeting:/cal: placeholder ids with a 400.

Bartib's log file only has minute precision and no task linkage, so _read_activities() joins each parsed row back to its task_time_tracking record via a new _tracking_task_ids() helper that truncates DB timestamps to the minute and matches on started_at. A single get_all_todoist_mappings() call (not one query per activity) then supplies each activity's note_url. Activities annotate todoist_task_id/note_url, excluding meeting:/cal: placeholders so ad-hoc and calendar-imported entries never show a Note button.

Edit modal: added an #edit-modal-note placeholder next to Save, populated in openEditModal() from the activity's todoist_task_id/note_url - "Open Note" (reusing the existing openNote()) when a mapping exists, "Create Note" (new createActivityNote(), calling /api/activity/note) otherwise. No button when there's no linked task.

Modified: src/taskbridge/web_ui.py. Added: tests/unit/test_web_ui.py (9 cases covering the task-id/time join, activity annotation, and get-or-create note logic with a real sqlite Database and mocked TodoistAPI/config). Full suite (252 tests) passes; ruff check/format and ty check clean on changed files.
<!-- SECTION:NOTES:END -->
