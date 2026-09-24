---
id: TASK-43
title: Add time/percent toggle to web UI daily report panel
status: Done
assignee:
  - '@iross'
created_date: '2026-09-02 15:56'
updated_date: '2026-09-02 15:56'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The daily report panel in the time-tracking web UI always shows client/project/label breakdowns as absolute durations. A quick toggle to show each line as a percentage of the day's total tracked time makes it easier to see where the day actually went at a glance, without doing the math by hand.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Report panel shows a toggle control that switches the client, project, and label breakdown values between absolute duration and percent-of-day-total
- [x] #2 The day's total duration in the report heading always stays an absolute duration, since a percentage of itself is meaningless
- [x] #3 The toggle state persists across page reloads
- [x] #4 Switching days (scrolling the activity list) keeps the previously chosen display mode
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a reportPercentMode client-side flag (persisted via localStorage) and a fmtAmount(secs, totalSecs) helper that renders either fmtDur(secs) or a rounded percent of totalSecs.
2. Add a small toggle control rendered in the report-heading (report-toggle CSS), wired to toggleReportPercent(), which flips the flag and re-renders the currently-visible day via a tracked lastReportDayKey.
3. Swap the client/project/label row values in renderReport() to use fmtAmount(); leave the heading's day total as an absolute duration always.
4. Manually verify via `taskbridge time serve` that the toggle renders, flips display mode, and survives a page reload.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added a client-only reportPercentMode toggle (persisted in localStorage) to the daily report panel. A new fmtAmount(secs, totalSecs) helper renders either the existing fmtDur() output or Math.round(secs/totalSecs*100) + '%'; the client/project/label breakdown rows now call it, while the heading's day total always stays an absolute duration since a percentage of itself is meaningless.

The toggle control (report-toggle) lives in the report-heading, which is regenerated on every renderReport() call (the panel's day changes as you scroll the activity list via the existing IntersectionObserver), so a lastReportDayKey variable tracks which day is currently shown and toggleReportPercent() re-renders that same day after flipping the flag - clicking the toggle doesn't reset to today's summary.

Modified: src/taskbridge/web_ui.py (CSS for .report-heading/.report-toggle, JS state/helpers, renderReport()). No backend changes - this is a pure display-mode toggle over data already sent to the client. Verified by serving `taskbridge time serve` and confirming the page renders with the new toggle markup; existing test suite (252 tests) is unaffected since no Python logic changed. ruff check/format and ty check clean, prek hooks pass.
<!-- SECTION:NOTES:END -->
