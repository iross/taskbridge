---
id: TASK-30
title: Add click-to-backfill for untracked gaps in web UI
status: Done
assignee:
  - '@claude'
created_date: '2026-07-07 16:34'
updated_date: '2026-11-04 22:54'
labels:
  - web-ui
  - time-tracking
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The timeline shows gap indicators for >10 min of untracked time between activities, but they are display-only. Reconstructing untracked time currently means manually opening the log form and re-entering times. Making gaps clickable turns backfilling into a two-click action and removes the most tedious part of keeping the log complete.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Clicking a gap indicator opens the existing log/start form prefilled with the gap's start and end times
- [x] #2 User can adjust times and pick a project/task before saving
- [x] #3 Submitting creates a bartib entry covering the gap and refreshes the timeline so the gap shrinks or disappears
- [x] #4 Gaps remain non-interactive for the currently running activity's open end
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Server: /api/start accepts an optional date (YYYY-MM-DD) for From+To entries; parse/validate the window in a helper; only stop the running session when starting a live one
2. UI: gap indicators carry their start/end, are clickable, and prefill the Start New form (From/To + backfill date banner with a clear button)
3. Submit sends the date; success clears the backfill and the timeline refresh shrinks/removes the gap
4. Tests for the window helper and the handler (past-day entry, active session untouched, bad input)
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Gap indicators (>10 min between two finished-adjacent activities) carry data-from/data-to and are clickable. A click prefills Start New's From/To, records the gap's day, shows a 'Backfilling a gap on <day> - clear' note and focuses Description; project, task and times stay editable.
- startTracking sends date (YYYY-MM-DD) with a backfill and refuses to submit one without a To. Success clears the backfill; the normal status refresh re-renders the timeline, so a fully filled gap disappears and a partial fill leaves a smaller gap.
- Server: new _start_window(body) parses date/time_from/time_to (date defaults to today, is only valid with both times, To must follow From) and returns 400 on bad input before anything changes.
- Behaviour change: /api/start with both From and To now writes the completed entry without stopping the running session. Before, any From+To entry also stopped whatever was being tracked.
- AC4: the open end of a running activity never had a gap row, and gap rows still need the older activity to have stopped, so it stays non-interactive.
- Verified with a headless Chrome click-through against a scratch bartib file: click 60 min gap -> 10:00/11:00 prefilled -> submit -> entry written, gap gone.
- Files: src/taskbridge/web_ui.py, tests/unit/test_web_ui.py
<!-- SECTION:NOTES:END -->
