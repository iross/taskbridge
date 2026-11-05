---
id: TASK-56
title: Add today's date heading when opening a task note
status: Done
assignee:
  - '@claude'
created_date: '2026-11-05 14:47'
updated_date: '2026-11-05 14:48'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Task notes are worked in as a running log under one H1 per day (e.g. '# 05.November.2026'). Opening a note from taskbridge should land it ready for today's entries instead of needing the heading typed by hand.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Opening a task note from the CLI or the web UI appends '# DD.Month.YYYY' for today when the note has no such heading
- [x] #2 A note that already has today's heading is left unchanged
- [x] #3 Creating notes without opening them (sync, backlog archive, task note --no-open) does not add a heading
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. task_notes: day_heading + ensure_day_heading(note_path, day)
2. Call it from task note (when opening) and the web UI's _get_or_create_task_note
3. Tests: new note, existing heading, other days' headings, no trailing newline, missing file
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- task_notes.day_heading(day) -> '# DD.Month.YYYY' (matches headings already in the vault); ensure_day_heading(path, day=today) appends it after one blank line unless a line already equals it (trailing spaces ignored; '## ...' doesn't count). Returns whether it wrote.
- Called from the CLI 'task note' only when opening, and from web_ui._get_or_create_task_note, which backs both web UI note buttons. Sync and backlog archive create notes through other paths and are unaffected.
- A note missing on disk (moved/deleted in Obsidian) is left alone rather than recreated.
- Only the heading is added; no starter bullet.
- Files: src/taskbridge/task_notes.py, src/taskbridge/main.py, src/taskbridge/web_ui.py, tests/unit/test_task_notes.py, tests/unit/test_web_ui.py
<!-- SECTION:NOTES:END -->
