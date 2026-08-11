---
id: TASK-40
title: Add taskbridge inbox open command to launch an item's native URI
status: Done
assignee: []
created_date: '2026-08-07 18:53'
updated_date: '2026-08-11 01:55'
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
- [x] #1 'taskbridge inbox open <index>' re-runs the same scan/report logic to resolve <index> to the same item, then launches its URI via the macOS 'open' command
- [x] #2 Works uniformly across every source (Obsidian, Todoist, Mail, Drafts) since launching needs no per-source logic beyond the URI string itself
- [x] #3 Clear error when the index is out of range or no items are currently reported
- [x] #4 Unit tests cover index resolution and the shell-out call via a mocked subprocess, not an actual 'open' invocation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add `inbox open <index>` command in main.py, re-running inbox.scan_all(config_manager, profile) to get the same ordered item list the report would show
2. 1-based index resolves to items[index-1]; out-of-range or empty list both print a clear error and exit 1
3. Launch item.uri via subprocess.run(["open", uri]) - works uniformly across sources since it only touches the URI string, no per-source branching
4. Unit tests: index resolution (valid/out-of-range/zero/negative), empty-items error, mocked subprocess.run call verification
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added `inbox open <index> [--profile]` in main.py: re-runs inbox.scan_all() with the same config/profile to reproduce the reports item ordering, resolves the 1-based index, and shells out to `open <uri>`. Empty item list and out-of-range index both print a clear error and exit 1. No per-source branching - it only ever touches item.uri, so Todoist/Mail/Drafts items (once those scanners land) need no changes here. Tests: tests/unit/test_inbox.py TestInboxOpenCommand (5 CliRunner cases, mocked subprocess.run). Full suite (236 tests) passes. ruff check/format clean; the two pre-existing ty check errors in main.py predate this branch.
<!-- SECTION:NOTES:END -->
