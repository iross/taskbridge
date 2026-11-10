---
id: TASK-57
title: Show today's tasks first in the web UI task dropdown
status: Done
assignee:
  - '@claude'
created_date: '2026-11-10 14:05'
updated_date: '2026-11-10 14:06'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Start New form's Todoist Task dropdown lists tasks in Todoist's default order, so the tasks planned for today are mixed in with (or cut off by) everything else. Putting them first makes the common case a single click.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Order within each group is otherwise unchanged
- [x] #2 Tasks with no due date or a malformed one sort with the not-today group
- [x] #3 Tasks due today appear first, then overdue tasks, then all others, for a selected project and for all tasks
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Sort _get_todoist_tasks output by a due<=today key (stable)
2. Unit tests: date-only and datetime dues, overdue, future, none, malformed
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- _get_todoist_tasks (backs /api/tasks for both the per-project and all-tasks picker) stable-sorts by _picker_rank: 0 due today (date or datetime), 1 overdue, 2 everything else incl. no due or an unparsable one.
- Split today from overdue after checking real data: 22 tasks were today-or-overdue, with overdue ones back to April crowding out today's.
- Within a group Todoist's order is kept (today's timed tasks are not re-sorted by time).
- Files: src/taskbridge/web_ui.py, tests/unit/test_web_ui.py
<!-- SECTION:NOTES:END -->
