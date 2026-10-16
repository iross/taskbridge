---
id: TASK-47
title: Add Obsidian Base view for archived backlog tasks
status: To Do
assignee: []
created_date: '2026-10-16 17:56'
labels:
  - obsidian
dependencies:
  - TASK-45
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Consistent frontmatter on archived backlog notes only pays off if they can be browsed together; an Obsidian Base gives a table view across projects and repos.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A 'Backlog Archive.base' in the vault's views/ folder lists every note with a backlog_id, showing project, repo, title, completed date and tags
- [ ] #2 The view can be grouped or filtered by project and repo
- [ ] #3 taskbridge backlog archive creates the base on first run if missing and never overwrites an existing one
<!-- AC:END -->
