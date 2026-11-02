---
id: TASK-52
title: >-
  Add interactive time cleanup command to merge similar task names in bartib
  history
status: Done
assignee:
  - '@claude'
created_date: '2026-11-02 16:21'
updated_date: '2026-11-02 16:24'
labels:
  - time-tracking
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Time entries for the same piece of work end up under slightly different descriptions (typos, plurals, casing), which splits them into separate rows in time reports. A cleanup command lets the user review groups of near-duplicate task names and merge them, rewriting bartib history so reports pick the merge up.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Similar task names within the same client/project are proposed as merge groups; names differing only in numbers are not grouped
- [x] #2 Each group is shown with entry counts and tracked time and the user decides per group: accept, skip, choose or type the canonical name, pick a subset of variants, or quit
- [x] #3 Nothing is written until the user confirms a final summary; --dry-run never writes
- [x] #4 Accepted merges rewrite matching bartib entries to the canonical name; per-entry #tags, times, projects and unrelated lines are untouched
- [x] #5 A timestamped backup of the bartib file is written before any change
- [x] #6 time report totals per project are unchanged and merged entries appear as one row after cleanup
- [x] #7 README documents the command
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. cleanup.py: pure similarity helpers (normalize, similar, cluster_similar_names) with digit guard
2. main.py: find_cleanup_clusters / apply_cleanup_mapping / rename_bartib_tasks (backup + rewrite) keyed on resolved (client, project)
3. main.py: interactive review loop and `time cleanup` command with --threshold and --dry-run
4. Unit tests for clustering, rewrite, review prompts via CliRunner; smoke run against a temp bartib file
5. README section
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added `taskbridge time cleanup` (--threshold, --dry-run).

Approach: names are clustered per report group (resolved client/project, same resolver as build_report_entries) on their clean description (#tags stripped). cleanup.py holds the pure similarity logic (normalized difflib ratio, default 0.85; names whose numbers differ never match; greedy grouping against each group first name so edit chains do not drag in unrelated names). main.py reads the log, finds clusters, runs an interactive per-cluster review (y / n / 1-N canonical / e edit / s subset / q), shows a summary, confirms, then rewrites.

Decisions: scope is bartib history only, same-project only (user choice). The mapping is applied to a fresh read of the file, matching by (group, old name), so entries added meanwhile are renamed too. Only the description changes; each line keeps its own #tags, time range and raw project; comment/blank/malformed lines are untouched. Timestamped backup (<file>.bak-<ts>) is written before the rewrite. Rejected groups are not remembered between runs. DB tracking records are not touched (reports read the bartib file).

Files: src/taskbridge/cleanup.py, src/taskbridge/main.py, tests/unit/test_cleanup.py, README.md. 457 unit tests, ruff and ty pass; smoke-run against a temp log and a dry run on a copy of the real log.
<!-- SECTION:NOTES:END -->
