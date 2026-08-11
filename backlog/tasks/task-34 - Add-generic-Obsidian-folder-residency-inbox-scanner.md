---
id: TASK-34
title: Add generic Obsidian folder-residency inbox scanner
status: Done
assignee: []
created_date: '2026-08-07 18:53'
updated_date: '2026-08-11 01:48'
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
- [x] #1 Scanner accepts a list of {label, path} configs from config.yaml
- [x] #2 Returns item count, item paths, and age (days since mtime) per configured folder
- [x] #3 Works against any folder path without Obsidian-specific assumptions beyond being a directory of markdown files
- [x] #4 Unit tests cover empty folder, stale items, and missing/misconfigured path
- [x] #5 Each returned item includes an obsidian:// URI (via a new vault-relative-path URL helper, since the existing generate_obsidian_url is hardcoded to the 10 Projects/ prefix) so it can be opened directly, not just its raw file path
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add InboxItem dataclass and scan_obsidian_folders() in new src/taskbridge/inbox.py
2. Extract Config.generate_obsidian_file_url() (vault-relative path -> URI) out of the existing generate_obsidian_url(), which was hardcoded to 10 Projects/
3. Add Config.get_inbox_folders() reading an inbox_folders list of {label, path} from config.yaml (path relative to vault root)
4. scan_obsidian_folders(configs, config_manager) lists *.md files directly in each folder (non-recursive), computes age from mtime, builds URI
5. Unit tests: empty folder, stale items (age calc), missing/misconfigured path, multiple folders
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added src/taskbridge/inbox.py with scan_obsidian_folders() + InboxItem dataclass. Config gained get_inbox_folders() and generate_obsidian_file_url() (extracted from generate_obsidian_url, which was hardcoded to the 10 Projects/ prefix and could not address 00 Inbox/ or 30 Resources/37 Literature/). A missing/misconfigured folder yields no items for that entry rather than raising. Tests: tests/unit/test_inbox.py, tests/unit/test_config.py (10 cases). ruff check/format and ty check pass.
<!-- SECTION:NOTES:END -->
