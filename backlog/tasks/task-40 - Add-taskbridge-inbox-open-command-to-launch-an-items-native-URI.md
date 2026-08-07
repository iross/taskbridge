---
id: TASK-40
title: Add taskbridge inbox open command to launch an item's native URI
status: To Do
assignee: []
created_date: '2026-08-07 18:53'
labels: []
dependencies:
  - TASK-36
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Let a specific item from the inbox report be launched directly in its native app (Mail to reply, Obsidian to read the note, Todoist/Drafts likewise), so the report isn't just informational but the actual jumping-off point for action. Opening a URI is navigation, not mutation - no tracked state changes, so this stays in v0 scope alongside the read-only report.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 'taskbridge inbox open <index>' re-runs the same scan/report logic to resolve <index> to the same item, then launches its URI via the macOS 'open' command,Works uniformly across every source (Obsidian, Todoist, Mail, Drafts) since launching needs no per-source logic beyond the URI string itself,Clear error when the index is out of range or no items are currently reported,Unit tests cover index resolution and the shell-out call via a mocked subprocess, not an actual 'open' invocation
<!-- AC:END -->
