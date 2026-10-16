---
id: TASK-46
title: Add git and PR provenance to archived backlog task notes
status: To Do
assignee: []
created_date: '2026-10-16 17:56'
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
An archived backlog task is more useful as a record when it shows where the work actually happened: the commits that implemented it and the PR that merged it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Archived notes get a Provenance section listing commits whose messages mention the task ID; matching is case-insensitive and zero-padding aware (task-09 = TASK-9) and task-4 does not match task-43
- [ ] #2 Commits link to GitHub when the repo origin is GitHub; otherwise they show the short SHA
- [ ] #3 Associated PRs are listed with title and URL (via gh) when available
- [ ] #4 A missing gh, non-GitHub remote, or API failure prints a warning and the note is still archived without PR links
- [ ] #5 Tasks with no matching commits get no Provenance section
<!-- AC:END -->
