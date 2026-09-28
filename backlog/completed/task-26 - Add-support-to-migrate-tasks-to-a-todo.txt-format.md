---
id: TASK-26
title: Add support to migrate tasks to a todo.txt format
status: Done
assignee:
  - '@iross'
created_date: '2026-06-15 17:52'
updated_date: '2026-06-15 18:18'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Maintain a todo.txt file that stays in sync with Todoist tasks. TaskBridge writes and updates this file automatically after any command that changes task state, giving users a portable, app-agnostic snapshot that works with any todo.txt-compatible tool (topydo, todotxt-cli, etc.). A one-time export command is also provided for the initial write or manual refresh.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A `todo_txt_path` setting is configurable via `taskbridge config` (optional; if unset all todo.txt sync is silently skipped)
- [x] #2 A `taskbridge export todo-txt [OUTPUT_FILE]` command performs a full regeneration of the file from current Todoist state
- [x] #3 After `task done`, `sync notes`, `sync projects`, and `sync jira`, the configured todo.txt file is automatically regenerated
- [x] #4 Active tasks are formatted per the todo.txt spec: `(PRIORITY) YYYY-MM-DD content +Project @label due:YYYY-MM-DD`
- [x] #5 Priority is mapped correctly: Todoist p1 (API priority 4) → `(A)`, p2 → `(B)`, p3 → `(C)`, p4 (API priority 1) → no priority marker
- [x] #6 Completed tasks are included with an `x YYYY-MM-DD` prefix (completion date)
- [x] #7 Project name is appended as a `+ProjectName` tag (spaces replaced with underscores)
- [x] #8 Labels are appended as `@label` context tags
- [x] #9 Due dates are appended as `due:YYYY-MM-DD` key-value extension fields
- [x] #10 Task creation date (from `created_at`) is included as the ISO date field after the priority marker
- [x] #11 Unit tests cover the formatting function with representative cases (all priorities, completed tasks, labels, projects with spaces, due dates)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add `todo_txt_path` to `config.py` with getter/setter; add configuration prompt to `taskbridge config` (or a new `taskbridge config todo-txt` subcommand)
2. Implement `format_task_as_todo_txt(task: TodoistTask, project_name: str) -> str` helper: map priority int→letter, handle `x YYYY-MM-DD` prefix for completed tasks, sanitize project name, append labels as @tags, append due date as key-value
3. Implement `write_todo_txt(path: str)` that fetches all tasks (active + recently completed) and projects from the Todoist API, formats each line, and atomically writes the file
4. Add `export_app` typer sub-app to `main.py` and wire up `taskbridge export todo-txt [OUTPUT_FILE]` to call `write_todo_txt()`
5. Add a `_sync_todo_txt()` helper that reads `todo_txt_path` from config and calls `write_todo_txt()` if configured; call it at the end of `task_done`, `sync_notes`, `sync_projects`, and `sync_jira`
6. Write unit tests in `tests/unit/` covering the formatting function; integration path tested via the export command
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented todo.txt export and auto-sync. Added: `format_task_as_todo_txt()` formatter, `write_todo_txt()` atomic file writer, `_fetch_todo_txt_lines()` (fetches active + best-effort completed via filter), `_sync_todo_txt()` silent hook, `taskbridge config todo-txt` command, `taskbridge export todo-txt [OUTPUT_FILE]` command. Hooked sync into task_done, sync_notes, sync_projects, sync_jira. Added `completed_at` field to TodoistTask dataclass. 16 unit tests in tests/unit/test_todo_txt.py cover all formatting cases.
<!-- SECTION:NOTES:END -->
