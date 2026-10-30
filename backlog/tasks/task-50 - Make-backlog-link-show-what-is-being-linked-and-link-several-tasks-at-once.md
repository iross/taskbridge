---
id: TASK-50
title: Make backlog link show what is being linked and link several tasks at once
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-30 15:32'
updated_date: '2026-10-30 15:34'
labels:
  - backlog
  - todoist
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
taskbridge backlog link opens the Todoist picker without saying which backlog task is being linked, so the user has to look the task up separately. Linking is also one task at a time, though many backlog tasks usually share one parent. Linking should show the backlog tasks involved and handle a batch in one step.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The Todoist parent picker shows the ID and title of every backlog task being linked
- [x] #2 taskbridge backlog link [TASK_IDS...] [--to PARENT] links all named tasks to one parent; PARENT may be a Todoist ID or URL, and without --to the parent is picked with fzf
- [x] #3 With no task IDs, an fzf multi-select lists the repo's backlog tasks with ID, title, status and current link, with a preview of the task, and every chosen task is linked
- [x] #4 The currently time-tracked Todoist task, if any, is listed first in the parent picker
- [x] #5 Each linked task is reported with its ID and title; an unknown task ID fails before anything is changed
- [x] #6 README documents the new usage
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. backlog.summarize for ID/title/status/parent
2. Shared _run_fzf (fzf check, header, extra args); task select and the parent picker use it
3. Backlog multi-picker with preview; link command takes task IDs + --to
4. Tests with fzf faked at the subprocess boundary; real fzf options checked with --filter
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- `taskbridge backlog link [TASK_IDS...] [--to PARENT] [--repo]` replaces the single-task `link TASK [PARENT]` form.
- No task IDs: fzf --multi over every task file, newest first, rows `ID  status  🔗  title` with the file path hidden in a tab-separated field used for the `cat {2}` preview (and not matched by search).
- Parent picker: header lists `ID  title` of each task being linked; the currently time-tracked Todoist task is moved to the top of the list.
- All backlog task IDs are resolved (and repeated IDs collapsed) before Todoist is contacted, so an unknown ID changes nothing. Output: one `🔗 ID  title` line per task, then the parent.
- main.py: new _run_fzf (fzf check + invocation, shared with pick_task_with_fzf and so task select), _pick_backlog_tasks, _open_tasks_current_first, _resolve_parent; backlog.py: TaskSummary/summarize.
- Verified: 434 tests; mutation checks on ordering, header, multi-select, de-duplication and the 🔗 marker all caught; real fzf accepts the options and returns the hidden path (checked with --filter). The interactive picker itself was not driven from here.
<!-- SECTION:NOTES:END -->
