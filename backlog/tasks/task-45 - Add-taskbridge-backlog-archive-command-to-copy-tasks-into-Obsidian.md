---
id: TASK-45
title: Archive linked backlog tasks into their parent Todoist task's note
status: To Do
assignee: []
created_date: '2026-10-16 17:56'
updated_date: '2026-10-30 15:02'
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
- [ ] #1 taskbridge backlog archive [IDS...] [--done] [--repo PATH] [--dry-run] [--force] archives the chosen tasks from the repo (default: cwd); --done selects every task with status Done (in tasks/ or completed/)
- [ ] #2 A task's parent is the Todoist task whose URL is in its references (canonical and slug URL forms both recognised); tasks with no Todoist reference are skipped and listed in a warning, and a task with more than one is skipped with an error
- [ ] #3 Each archived task is appended to the parent's Obsidian task note as a section headed with repo, ID and title, containing description, acceptance criteria as checkboxes, plan and implementation notes, with no backlog marker comments
- [ ] #4 The parent note is created the same way the web UI and task note command create it when it does not exist yet
- [ ] #5 The parent note's frontmatter lists every archived task in backlog_tasks as <repo>/<ID> and carries the tags backlog and backlog/<repo>; other frontmatter and body content are left unchanged
- [ ] #6 Re-running skips and reports tasks whose section is already in the parent note; --force replaces only that task's section
- [ ] #7 If the parent has no note and cannot be fetched from Todoist (completed or deleted) the task is skipped with a warning naming the parent
- [ ] #8 Repo files are never modified; --dry-run prints each task's parent note path and writes nothing
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation pointers:
- Parse task files directly (YAML frontmatter + SECTION/AC markers); yaml is already a dependency.
- Reuse the get-or-create note logic behind the web UI (_get_or_create_task_note in web_ui.py) and task note; move it somewhere shared rather than duplicating it.
- New module src/taskbridge/backlog_archive.py; backlog_app typer group in main.py.
- Mark each appended section with a hidden comment keyed by <repo>/<ID> so re-runs and --force can find it.
Out of scope: sweeping all repos under ~/projects, an inbox source for done-but-unarchived tasks, moving/deleting tasks from repos, a command to set the link (manual: backlog task edit <id> --ref <url>).
<!-- SECTION:NOTES:END -->
