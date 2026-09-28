---
id: task-23
title: Create daily report for email
status: Done
assignee: []
created_date: '2026-02-25 20:11'
updated_date: '2026-02-25 20:41'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create a daily summary report, pulling data from bartib over a given timespan,
categorizing it by client/project, and providing percentage of time spent for
that timespan in that category

Output should look something like:

CHTC 0.6
  - Project 1: 0.9
    - Description
  - Project 2: 0.1
PATh 0.4
  - Project 1: 1.0
    - Description
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 - [ ] `taskbridge time report` defaults to today's tracked time
- [x] #2 - [ ] Accepts `--date YYYY-MM-DD` to report on a specific day, and `--from`/`--to` for a range
- [x] #3 - [ ] Groups entries by client (first `::` segment) then project (second segment); tags (third+) excluded from hierarchy
- [x] #4 - [ ] Client rows show fraction of total tracked time
- [x] #5 - [ ] Project rows show fraction of that client's time (so projects within a client sum to 1.0)
- [x] #6 - [ ] Descriptions (task names) are listed under each project
- [x] #7 - [ ] Active (unstopped) session contributes time up to now
- [x] #8 - [ ] Prints a total hours header line
- [x] #9 - [ ] Entries with no `::` separator are grouped under an `(other)` client
- [x] #10 - [ ] Unit tests cover the aggregation and formatting logic
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
["1. Add `get_tracking_in_range(from_dt, to_dt)` to `database.py`", "2. Add `parse_project_segments(project_name)` helper in `main.py` → `(client, project)`", "3. Add `build_daily_report(records, now)` pure function that aggregates and returns structured data", "4. Add `time report` command with `--date`, `--from`, `--to` options", "5. Write unit tests for the DB method, the segment parser, and the aggregation function"]
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Revised implementation to read from the bartib activity file directly instead of the taskbridge DB. The DB approach caused a discrepancy: `time list` (which reads from bartib) and `time report` showed different capitalization for the same sessions because they were reading from different data sources.\n\nFinal implementation:\n- `parse_bartib_file(from_dt, to_dt)` reads `BARTIB_FILE` env var, parses lines of the format `YYYY-MM-DD HH:MM - YYYY-MM-DD HH:MM | Project | Description` (active sessions omit the stop time), and filters by start time range\n- `time report` now calls `parse_bartib_file` instead of `db.get_tracking_in_range`\n- Clear error raised if `BARTIB_FILE` is not set\n- 5 additional tests in `TestParseBartibFile` (22 total in test_report.py)\n- `get_tracking_in_range` remains in the DB for completeness but is no longer used by the report command\n- Files modified: src/taskbridge/main.py, tests/unit/test_report.py
<!-- SECTION:NOTES:END -->
