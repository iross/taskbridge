---
id: TASK-37
title: Add Todoist Inbox project scanner
status: Done
assignee: []
created_date: '2026-08-07 18:53'
updated_date: '2026-08-11 01:54'
labels: []
dependencies:
  - TASK-36
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the inbox report to cover Todoist's Inbox project, reusing the existing TodoistAPI client rather than adding new HTTP logic. Registered under module name 'todoist_inbox' for profile toggling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Scanner fetches tasks currently in the configured Todoist Inbox project
- [x] #2 Task count and oldest-task age are included in 'inbox report' output when the 'todoist_inbox' module is enabled for the active profile
- [x] #3 Uses existing TodoistAPI/config patterns (no new auth mechanism)
- [x] #4 Unit tests cover empty inbox and stale-task cases with mocked API responses
- [x] #5 Each returned task includes an openable URI (https://todoist.com/showTask?id=<id>, which opens the Todoist app via universal link if installed)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Rename InboxItem.path -> InboxItem.description (a Todoist task content string is not a filesystem path; generalizes the field across sources) and update the Obsidian scanner + report display accordingly
2. Add scan_todoist_inbox(config_manager): find the project with is_inbox_project=True via existing TodoistAPI.get_projects(), fetch its tasks, compute age from task.created_at via datetime.fromisoformat (matches existing convention in database.py), build https://todoist.com/showTask?id=<id> URIs
3. No token / no inbox project found -> return [] rather than raising, matching the folder scanner precedent
4. Add todoist_inbox to INBOX_MODULES and wire into scan_all()
5. Unit tests: empty inbox, stale-task age calc, missing inbox project, no token configured, URI format - all with mocked TodoistAPI
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added scan_todoist_inbox() to inbox.py: finds the is_inbox_project=True project via existing TodoistAPI, fetches its tasks, computes age from task.created_at via datetime.fromisoformat (matches database.py convention), builds https://todoist.com/showTask?id=<id> URIs. No token or no inbox project both resolve to [] rather than raising. Added todoist_inbox to INBOX_MODULES and wired into scan_all(). Deviation: renamed InboxItem.path -> InboxItem.description since a Todoist task content string is not a filesystem path - updated the Obsidian scanner and inbox report display (task-34/36 code) to match; their satisfied AC and Done status are unaffected. Tests: tests/unit/test_inbox.py TestScanTodoistInbox + TestScanAll additions (23 cases total in the file). Full suite (231 tests) passes. ruff check/format clean.
<!-- SECTION:NOTES:END -->
