---
id: TASK-32
title: Add project picker for reassigning entries in web UI edit modal
status: To Do
assignee: []
created_date: '2026-07-07 16:39'
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
- [ ] #1 Edit modal lets the user pick a project from the same sources as the start form (recent bartib projects and Todoist project hierarchy) instead of typing the bartib string from memory
- [ ] #2 Free-text entry remains possible for projects not in the list
- [ ] #3 Reassignment works for both completed entries and the currently running entry
- [ ] #4 Saving updates the bartib entry and the refreshed timeline shows the entry under the new project with its client color
<!-- AC:END -->
