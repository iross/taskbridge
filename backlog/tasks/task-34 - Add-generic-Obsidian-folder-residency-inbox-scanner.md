---
id: TASK-34
title: Add generic Obsidian folder-residency inbox scanner
status: To Do
assignee: []
created_date: '2026-08-07 18:53'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Provide a reusable scanner that treats presence in a configured vault folder as 'unprocessed' and absence as 'processed', with per-item age. Backs both the 00 Inbox folder and the Readwise literature folder without source-specific code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Scanner accepts a list of {label, path} configs from config.yaml,Returns item count, item paths, and age (days since mtime or frontmatter date) per configured folder,Works against any folder path without Obsidian-specific assumptions beyond being a directory of markdown files,Unit tests cover empty folder, stale items, and missing/misconfigured path,Each returned item includes an obsidian:// URI (via the existing generate_obsidian_url helper) so it can be opened directly, not just its raw file path
<!-- AC:END -->
