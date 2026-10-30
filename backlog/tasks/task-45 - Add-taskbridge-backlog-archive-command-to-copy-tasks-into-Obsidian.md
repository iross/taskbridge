---
id: TASK-45
title: Archive linked backlog tasks into their parent Todoist task's note
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-16 17:56'
updated_date: '2026-10-30 15:18'
labels:
  - obsidian
  - backlog
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Finished backlog.md tasks hold design rationale and implementation notes that belong with the work they were part of. Per ADR-004 a backlog task names its parent taskbridge (Todoist) task by URL in its references, and many backlog tasks can share one parent. Archiving appends each task to the parent's Obsidian note, so the note becomes the record of how that piece of work was done. Copying (not moving) keeps the repo's task history intact and avoids backlog.md reusing IDs of deleted tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 taskbridge backlog archive [IDS...] [--done] [--repo PATH] [--dry-run] [--force] archives the chosen tasks from the repo (default: cwd); --done selects every task with status Done (in tasks/ or completed/)
- [x] #2 A task's parent is the Todoist task whose URL is in its references (canonical and slug URL forms both recognised); tasks with no Todoist reference are skipped and listed in a warning, and a task with more than one is skipped with an error
- [x] #3 Each archived task is appended to the parent's Obsidian task note as a section headed with repo, ID and title, containing description, acceptance criteria as checkboxes, plan and implementation notes, with no backlog marker comments
- [x] #4 The parent note is created the same way the web UI and task note command create it when it does not exist yet
- [x] #5 The parent note's frontmatter lists every archived task in backlog_tasks as <repo>/<ID> and carries the tags backlog and backlog/<repo>; other frontmatter and body content are left unchanged
- [x] #6 Re-running skips and reports tasks whose section is already in the parent note; --force replaces only that task's section
- [x] #7 If the parent has no note and cannot be fetched from Todoist (completed or deleted) the task is skipped with a warning naming the parent
- [x] #8 Repo files are never modified; --dry-run prints each task's parent note path and writes nothing
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. frontmatter.py: split/load/set-list helpers that leave other keys untouched; backlog.py uses them
2. task_notes.py: move resolve_project_info and the web UI get-or-create-note logic there so web UI and archive share it; config.task_note_path for dry-run
3. backlog_archive.py: parse task files by ## headings (marker comments optional, older files have none), select by IDs or --done, resolve parent from references, render section with begin/end markers, append or --force replace, update backlog_tasks + tags
4. Find the parent note via its DB mapping, falling back to 40 Archive/ when the project was archived (project archive does not update mappings)
5. taskbridge backlog archive command: per-task report, unlinked warning, exit 1 on errors; --dry-run writes nothing (no notes, mappings or comments)
6. Tests: unit for parsing/rendering/frontmatter/note updates/selection; CLI tests with mocked Todoist; end-to-end on a scratch vault + repo
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- `taskbridge backlog archive [IDS...] [--done] [--repo] [--dry-run] [--force]` (main.py) drives src/taskbridge/backlog_archive.py.
- Sections are parsed by `## ` headings, so 2025-era files without SECTION/AC markers work; markers and AC `#N` indexes are dropped, inner headings demoted, fenced code left alone, empty sections omitted. All 45 real task files in this repo parse.
- Each task is one section between `<!-- backlog:<repo>/<ID> -->` and `<!-- /backlog:<repo>/<ID> -->`; re-runs skip it, --force replaces exactly that span (byte-identical when the task is unchanged). A start marker without its end is an error and the note is left alone.
- Parent note: DB mapping first; if the mapped path is gone, the same path under 40 Archive/ (project archive moves folders without updating mappings); otherwise an error naming taskbridge map update. With no mapping, the note is created via the shared task_notes.get_or_create_task_note. A parent that Todoist cannot return (completed/deleted) with no note is skipped with an error.
- New src/taskbridge/frontmatter.py edits only the keys it changes (backlog_tasks, tags, references), leaving everything else as written; backlog.py now uses it too.
- New src/taskbridge/task_notes.py holds resolve_project_info (moved from main.py) and the get-or-create note logic (moved from web_ui.py) so the web UI and archive share it. config.task_note_path lets --dry-run report a new note's path without creating it.
- --done runs in task-number order; repo name is the repo directory name; tags are sanitized for Obsidian.
- Exit code 1 if any task failed; unlinked tasks are a warning (exit 0).
- Verified: 400 tests pass; mutation checks on the archive module all caught; real --dry-run on a scratch copy of this backlog against the real vault/DB/Todoist reported an append to an existing note and a new note, and changed neither.
- Tests: tests/unit/test_backlog_archive.py, test_frontmatter.py, test_task_notes.py (moved from test_web_ui.py).
<!-- SECTION:NOTES:END -->
