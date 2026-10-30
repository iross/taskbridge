---
id: TASK-47
title: Add Obsidian Base view for notes with archived backlog tasks
status: To Do
assignee: []
created_date: '2026-10-16 17:56'
updated_date: '2026-10-30 15:03'
labels:
  - obsidian
dependencies:
  - TASK-45
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Archived backlog tasks live inside their parent Todoist task's notes (TASK-45), which carry backlog_tasks and backlog/<repo> tags. An Obsidian Base gives a table across projects and repos of which pieces of work have archived backlog tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A 'Backlog Archive.base' in the vault's views/ folder lists every note whose frontmatter has backlog_tasks, showing project, client, note title, status and the linked backlog tasks
- [ ] #2 The view can be grouped or filtered by project, and filtered to one repo via its backlog/<repo> tag
- [ ] #3 taskbridge backlog archive creates the base on first run if missing and never overwrites an existing one
<!-- AC:END -->
