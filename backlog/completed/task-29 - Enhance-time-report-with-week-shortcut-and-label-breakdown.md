---
id: TASK-29
title: Enhance time report with week shortcut and label breakdown
status: Done
assignee:
  - Ian Ross
created_date: '2026-06-18 00:42'
updated_date: '2026-06-18 00:47'
labels: []
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The existing 'taskbridge time report' command is missing two useful features: a convenience flag for the current week so users don't have to manually specify date ranges, and a label breakdown section that surfaces time spent per label (e.g. meetings, ♾️ standing tasks). The label data is already encoded in the bartib project string's third '::' segment but is currently ignored by parse_project_segments.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `taskbridge time report --week` shows a report for the current Mon–Sun week
- [x] #2 The report output includes a label breakdown section showing fraction of total time per label
- [x] #3 Label data is parsed from the third `::` segment of the bartib project string (`client::project::tag1,tag2`)
- [x] #4 Labels that appear on zero tracked entries are omitted from the breakdown
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend parse_project_segments to return tags (third :: segment) as well as client/project\n2. Add tags field to ReportEntry dataclass\n3. Update build_report_entries to populate tags from the parsed project string\n4. Update format_report to append a label breakdown section\n5. Add --week flag to time_report command, computing Mon-Sun bounds for the current week\n6. Run tests and linting
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Extended parse_project_segments to return a third element (list of tags from the :: third segment). Added tags field to ReportEntry. Updated build_report_entries to populate tags. Updated format_report to append a Labels section (sorted by fraction of total, omitted when no tags present). Added --week flag to time_report that computes the Mon–Sun bounds for the current week. Updated all tests for the new signature and added three new tests for label breakdown behavior.
<!-- SECTION:NOTES:END -->
