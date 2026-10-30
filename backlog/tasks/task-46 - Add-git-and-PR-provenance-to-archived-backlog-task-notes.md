---
id: TASK-46
title: Add git and PR provenance to archived backlog task notes
status: To Do
assignee: []
created_date: '2026-10-16 17:56'
updated_date: '2026-10-30 15:03'
labels:
  - obsidian
  - backlog
  - git
dependencies:
  - TASK-45
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
An archived backlog task is more useful as a record when it shows where the work actually happened: the commits that implemented it and the PR that merged it. Since TASK-45 appends archived tasks to the parent Todoist task's note, this history belongs inside each task's appended section.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Commits link to GitHub when the repo origin is GitHub; otherwise they show the short SHA
- [ ] #2 Associated PRs are listed with title and URL (via gh) when available
- [ ] #3 A missing gh, non-GitHub remote, or API failure prints a warning and the note is still archived without PR links
- [ ] #4 Each task section appended by backlog archive gets a Provenance subsection listing commits whose messages mention the task ID; matching is case-insensitive and zero-padding aware (task-09 = TASK-9) and task-4 does not match task-43
- [ ] #5 Tasks with no matching commits get no Provenance subsection
<!-- AC:END -->
