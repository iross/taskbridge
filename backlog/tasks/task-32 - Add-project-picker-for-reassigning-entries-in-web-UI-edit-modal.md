---
id: TASK-32
title: Add project picker for reassigning entries in web UI edit modal
status: Done
assignee:
  - '@claude'
created_date: '2026-07-07 16:39'
updated_date: '2026-10-30 14:29'
labels:
  - web-ui
  - time-tracking
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The activity edit modal only offers a free-text project input, so moving an entry to a different project (e.g. from Inbox to PATh/Monthly_Report after forgetting to move the task in Todoist before starting tracking) requires typing the exact sanitized bartib project string from memory. The start form already has a proper picker with recent bartib projects and the Todoist client/project hierarchy; reassignment in the edit modal should be equally easy. Moving the underlying Todoist task to the correct project could be a follow-up task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Edit modal lets the user pick a project from the same sources as the start form (recent bartib projects and Todoist project hierarchy) instead of typing the bartib string from memory
- [x] #2 Free-text entry remains possible for projects not in the list
- [x] #3 Reassignment works for both completed entries and the currently running entry
- [x] #4 Saving updates the bartib entry and the refreshed timeline shows the entry under the new project with its client color
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. /api/projects: give each Todoist project the bartib string a start would produce (manual mapping, else root ancestor = client)
2. Edit modal: project input gets a datalist of recent bartib projects + Todoist projects (label shows Todoist path); free text still allowed
3. Editing the running entry also updates the active tracking record project/description so the current panel matches
4. Unit tests for bartib-string mapping and running-entry DB update
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- /api/projects now returns a `bartib` string per Todoist project, computed the same way a start on it would (manual config mapping wins; otherwise root ancestor = client, project = folder) without extra API calls (`_todoist_bartib_project` in web_ui.py).
- Edit modal project input is attached to a `project-list` datalist: recent bartib projects first, then Todoist projects labelled with their path, de-duplicated. Free text still works. The input clears on focus so the whole list shows (a prefilled datalist only suggests matches) and restores the old value on blur if left empty.
- Editing the running entry now also updates the active tracking record (project, description, and start if the minute changed) via new `Database.update_tracking_labels` + `_sync_active_tracking`, so the current panel and `time stop` agree with the log. Only applied when the edited line is the unstopped one.
- Tests: tests/unit/test_web_ui.py (bartib strings incl. nested + manual mapping + Todoist failure; reassign stopped/running entries, start change, no active record, stopped entry sharing the running start minute).
- Files: src/taskbridge/web_ui.py, src/taskbridge/database.py, tests/unit/test_web_ui.py
<!-- SECTION:NOTES:END -->
