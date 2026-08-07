---
id: TASK-37
title: Add Todoist Inbox project scanner
status: To Do
assignee: []
created_date: '2026-08-07 18:53'
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
- [ ] #1 Scanner fetches tasks currently in the configured Todoist Inbox project,Task count and oldest-task age are included in 'inbox report' output when the 'todoist_inbox' module is enabled for the active profile,Uses existing TodoistAPI/config patterns (no new auth mechanism),Unit tests cover empty inbox and stale-task cases with mocked API responses,Each returned task includes an openable URI (https://todoist.com/showTask?id=<id>, which opens the Todoist app via universal link if installed)
<!-- AC:END -->
