---
id: TASK-49
title: >-
  Add taskbridge backlog link command to set a backlog task's parent Todoist
  task
status: To Do
assignee: []
created_date: '2026-10-30 15:03'
labels:
  - backlog
  - todoist
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-004 links a backlog task to its parent taskbridge task by putting the Todoist task URL in the backlog task's references. Setting that by hand means finding the Todoist task ID and typing the URL; a command that reuses taskbridge's task picker makes linking a quick step during normal work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 taskbridge backlog link TASK-ID [TODOIST_TASK_ID] [--repo PATH] adds the canonical Todoist task URL to the backlog task's references
- [ ] #2 With no Todoist ID given the user picks the parent with the same picker as taskbridge task select
- [ ] #3 An existing Todoist reference on the task is replaced, not added to; other references are kept
- [ ] #4 An unknown backlog task ID or Todoist task ID fails with a clear error and changes nothing
- [ ] #5 The change is made so later backlog task edit runs keep the link
<!-- AC:END -->
