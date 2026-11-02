---
id: TASK-53
title: Add fzf picker to time cleanup for merging duplicate task names by hand
status: Done
assignee:
  - '@claude'
created_date: '2026-11-02 16:40'
updated_date: '2026-11-02 16:40'
labels:
  - time-tracking
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
String similarity cannot find duplicates that were worded differently (e.g. 'Fabaid Sync with Tony and Nova' and 'Fabaid chat with Nova and Tony'). The user needs to pick such names out of a project themselves and merge them, using the same keyboard-driven pickers as the rest of the CLI.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 time cleanup --manual lists projects and then every task name in the chosen project, with entry count, tracked time and last-used date, and the user marks the names that are one task
- [x] #2 After marking, the user picks which marked name to keep or types a new one; names with #tags are rejected
- [x] #3 The suggestion pass offers to continue into the picker; names shown reflect merges already accepted in that run
- [x] #4 Picked merges go through the same summary, confirmation, --dry-run and backup as suggested merges
- [x] #5 Esc backs out of each picker level without writing; README documents the mode
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extract variant collection from find_cleanup_clusters; track last-used date
2. fzf loop: project -> mark names -> keep/type name, composing into the shared mapping
3. time cleanup --manual and a browse offer after the suggestion pass
4. Tests with a scripted fzf; smoke run of real fzf through a pty; README
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added `time cleanup --manual` and a browse-by-hand offer after the suggestion pass.

Approach: three fzf levels (project -> mark names -> keep/type name) built on the existing fzf_args/_run_fzf helpers (browse keys j/k/x//, Esc backs out). Rows are indexed through a hidden tab-delimited first field so any description text maps back safely. Each merge is composed into the single {(client, project, old): new} mapping (compose_cleanup_mappings), and the pickers show names as they will be after the mapping, so manual picks stack on accepted suggestions; the existing summary, confirm, dry-run and backup apply unchanged. Variants gained a last_used date to help judge duplicates. User declined smarter word-overlap suggestions, so none were added.

Tests use a scripted fzf; real fzf was also driven through a pty (merged "Fabaid chat with Nova and Tony" into "Fabaid Sync with Tony and Nova", backup written). Files: src/taskbridge/main.py, tests/unit/test_cleanup.py, README.md. 464 unit tests, ruff, ty pass.
<!-- SECTION:NOTES:END -->
