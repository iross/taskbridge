---
id: TASK-54
title: Add --month option to time report
status: Done
assignee:
  - '@claude'
created_date: '2026-11-02 16:43'
updated_date: '2026-11-02 16:43'
labels:
  - time-tracking
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reporting a whole month currently needs --from/--to with computed dates. A --month option makes monthly reports a one-liner.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 time report --month with no value reports the current calendar month
- [x] #2 time report --month 10 reports the most recent October that is not in the future; YYYY-MM selects an exact month
- [x] #3 Invalid months and combining --month with --week/--date/--from/--to fail with a clear message
- [x] #4 README documents the option
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. month_range helper (current / N / YYYY-MM)
2. --month option on time report; command subclass fills in the value for a bare --month because typer has no optional-value options
3. Tests, smoke on real log, README
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added `time report --month [MONTH]`.

month_range() resolves "current", a number (most recent occurrence not after the current month, so --month 12 in Nov 2026 is Dec 2025) or YYYY-MM, raising ValueError otherwise; the existing handler prints it. Typer ignores click's is_flag/flag_value, so a TyperCommand subclass (_BareMonthCommand) inserts "current" after a bare --month before parsing; only public click API is used. --month combined with other range options is an error rather than silently taking precedence.

Files: src/taskbridge/main.py, tests/unit/test_report.py, README.md. Smoke-tested on the real log (--month 10, bare --month, combined-options error).
<!-- SECTION:NOTES:END -->
