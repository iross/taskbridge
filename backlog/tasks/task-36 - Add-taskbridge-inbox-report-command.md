---
id: TASK-36
title: Add taskbridge inbox report command
status: To Do
assignee: []
created_date: '2026-08-07 18:53'
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
- [ ] #1 'taskbridge inbox report' prints count + oldest-item age per configured source,Only sources enabled for the active profile are run or reported,Works with only the Obsidian scanner configured (no hard dependency on unbuilt adapters),Exits cleanly with a clear message when no sources are configured or enabled,Unit tests cover aggregation and formatting with mocked scanner results, including profile filtering,Report lists individual items (not just aggregate counts per source), each carrying its native URI, so a specific item can be identified and opened rather than only counted
<!-- AC:END -->
