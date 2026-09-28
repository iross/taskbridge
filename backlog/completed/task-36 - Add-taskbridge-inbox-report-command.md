---
id: TASK-36
title: Add taskbridge inbox report command
status: Done
assignee: []
created_date: '2026-08-07 18:53'
updated_date: '2026-08-11 01:51'
labels: []
dependencies:
  - TASK-34
  - TASK-35
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Give a single command that aggregates all configured, profile-enabled inbox scanners into one checklist, so outstanding items across sources are visible without checking each tool separately.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 'taskbridge inbox report' prints count + oldest-item age per configured source
- [x] #2 Only sources enabled for the active profile are run or reported
- [x] #3 Works with only the Obsidian scanner configured (no hard dependency on unbuilt adapters)
- [x] #4 Exits cleanly with a clear message when no sources are configured or enabled
- [x] #5 Unit tests cover aggregation and formatting with mocked scanner results, including profile filtering
- [x] #6 Report lists individual items (not just aggregate counts per source), each carrying its native URI, so a specific item can be identified and opened rather than only counted
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add inbox.scan_all(config_manager, profile) and inbox.enabled_modules(config_manager, profile), gated on a module registry tuple (currently just obsidian_inbox)
2. Add inbox.group_by_label(items) -> list of (label, count, oldest_age_days) sorted by label
3. Add inbox_app Typer sub-app + `inbox report --profile` command in main.py: prints a clear message if no modules are enabled, prints inbox-zero message if enabled but no items, otherwise prints grouped summary then a globally-indexed item list (URI included per item for later inbox open)
4. Unit tests: scan_all/enabled_modules/group_by_label logic, plus CliRunner tests for the report command covering no-modules-enabled, inbox-zero, and populated cases
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added inbox.enabled_modules()/scan_all()/group_by_label() in inbox.py, gated on the INBOX_MODULES registry (currently just obsidian_inbox). Wired a new inbox_app Typer group with `inbox report --profile`: distinguishes no-modules-enabled (clear message, early return) from enabled-but-empty (inbox zero message) from populated (grouped per-label summary + globally-indexed item list with paths, for task-40 to resolve later). Tests: tests/unit/test_inbox.py (CliRunner-based command tests + logic tests, 16 cases total). Full suite (224 tests) still passes. ruff check/format pass; the two pre-existing ty check errors in main.py (sources dict typing, sorted() overload) predate this change and are out of scope.
<!-- SECTION:NOTES:END -->
