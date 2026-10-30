---
id: TASK-49
title: >-
  Add taskbridge backlog link command to set a backlog task's parent Todoist
  task
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-30 15:03'
updated_date: '2026-10-30 15:09'
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
- [x] #1 taskbridge backlog link TASK-ID [TODOIST_TASK_ID] [--repo PATH] adds the canonical Todoist task URL to the backlog task's references
- [x] #2 With no Todoist ID given the user picks the parent with the same picker as taskbridge task select
- [x] #3 An existing Todoist reference on the task is replaced, not added to; other references are kept
- [x] #4 An unknown backlog task ID or Todoist task ID fails with a clear error and changes nothing
- [x] #5 The change is made so later backlog task edit runs keep the link
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. New backlog module: Todoist URL parse/format, task file lookup across tasks/ and completed/, rewrite of the references block
2. Extract the fzf picker from task select for reuse
3. backlog link command
4. Unit tests + integration test against the real backlog CLI; end-to-end run against Todoist on a scratch copy
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- src/taskbridge/backlog.py: todoist_task_url / todoist_task_id (canonical and browser slug URL forms), find_task_file (tasks/ and completed/, any spelling of the ID incl. zero padding and subtasks), read_references, set_parent_task.
- The references block is rewritten directly rather than via `backlog task edit --ref`, because the backlog CLI cannot edit tasks in completed/ and TASK-45 archives those too. Written in the CLI's own format; tests/integration/test_backlog_cli.py confirms a later `backlog task edit` keeps the link.
- main.py: `taskbridge backlog link TASK [PARENT] [--repo]`; PARENT may be an ID or pasted URL, omitted -> fzf picker over open tasks. pick_task_with_fzf extracted from `task select`.
- Found during end-to-end testing: Todoist returns 400 (not 404) for malformed task IDs, which crashed with a traceback. get_task now treats 400 like 404; network errors in `backlog link` give a clear message.
- Adjacent fixes: `task select` no longer prints a stray "❌ Error: 1" on cancel / no tasks / missing fzf (typer.Exit was caught by the catch-all); Todoist HTTP error logging now shows the response body (a 4xx Response is falsy, so it always printed "No response").
- Tests: tests/unit/test_backlog.py, tests/unit/test_todoist_api.py (get_task status codes), tests/unit/test_task_select.py (quiet exits), tests/integration/test_backlog_cli.py. Mutation-checked the backlog module and the task select fix.
- README: new "Linking backlog tasks to Todoist tasks" section.
<!-- SECTION:NOTES:END -->
