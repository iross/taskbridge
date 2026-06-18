---
id: TASK-27
title: Add ♾️ standing task support
status: To Do
assignee: []
created_date: '2026-06-17 13:04'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Establish a first-class concept of standing tasks — background work like email catchup or morning
focus that is always present and never closes. These tasks live in Todoist with a `♾️` label, sync
to todo.txt as `@♾️` context tags, and serve primarily as time-tracking anchors. They should stay
below the radar in normal views but be easily surfaced when needed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] Todoist tasks with the `♾️` label sync to todo.txt with an `@♾️` context tag (verify existing label→context mapping works end-to-end and document in README)
- [ ] During sync, if a `♾️` task has disappeared from Todoist's active task list (completed in Todoist), print a loud warning and skip marking it complete in todo.txt rather than silently completing it
- [ ] `taskbridge task list` and `taskbridge task select` accept a `--hide-standing` flag to exclude standing tasks from output
- [ ] `taskbridge task list` and `taskbridge task select` accept `-l ♾️` to show only standing tasks (verify existing `--label` filter works; document it)
- [ ] `taskbridge task done` warns and requires explicit confirmation before completing a task that carries the `♾️` label
- [ ] The standing task label used for all of the above is configurable in taskbridge config, defaulting to `♾️`
<!-- AC:END -->
