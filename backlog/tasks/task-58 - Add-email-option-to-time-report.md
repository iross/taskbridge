---
id: TASK-58
title: Add --email option to time report
status: Done
assignee:
  - '@claude'
created_date: '2026-11-10 15:09'
updated_date: '2026-11-10 15:09'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
time report was first built to paste into a daily status email (task-23) but has since become a terminal report: durations, dot leaders padded to 100 columns, ANSI bold and tag pills, a Labels section. None of that pastes cleanly into an email. An --email mode brings back the compact share-of-time summary.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 taskbridge time report --email prints a total-time header, then clients with their fraction of total time and projects with their fraction of that client's time
- [x] #2 Descriptions are listed under each project without durations or tags
- [x] #3 Output has no ANSI codes, dot leaders, Labels section or Daily breakdown
- [x] #4 --email combines with --date, --from/--to, --week and --month
- [x] #5 An empty period prints the same no-time message as the normal report
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. format_email_report(entries) in main.py: aggregate client/project/description seconds, render fractions to 2 decimals, largest first
2. --email flag on time report: print header with total and the email body, skip Daily section
3. Tests: fractions sum per level, ordering, no ANSI/tags, empty input, CLI flag with a range
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- format_email_report(label, entries) in main.py: header '<label> (<total>)', clients with share of total, '  - project: share' of the client, '    - description' lines; all largest first, 2 decimals so small projects don't round to 0.0. No ANSI, dot leaders, tags, Labels or Daily section.
- time report --email prints only that and returns before the normal output; it works with every range option since it runs after range resolution.
- Aggregation is a small separate pass rather than shared with format_report (second use; the dotted report also tracks tags and labels).
- No clipboard copy; pipe to pbcopy if wanted.
- Files: src/taskbridge/main.py, tests/unit/test_report.py, README.md
<!-- SECTION:NOTES:END -->
