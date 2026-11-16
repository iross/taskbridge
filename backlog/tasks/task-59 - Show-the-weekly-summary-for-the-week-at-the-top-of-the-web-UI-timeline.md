---
id: TASK-59
title: Show the weekly summary for the week at the top of the web UI timeline
status: Done
assignee: []
created_date: '2026-11-16 16:05'
updated_date: '2026-11-16 16:07'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The web UI report panel always summarises the current week, even when the timeline is scrolled back to days from the previous week. On a Monday the weekly summary is nearly empty while the timeline shows mostly last week. The weekly summary should follow the timeline the same way the daily summary already does.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Weekly summary covers the Mon–Sun week containing the topmost visible day of the timeline
- [x] #2 Weekly summary heading names the week shown (This Week / Last Week)
- [x] #3 Timeline reaches back to the Monday of the previous week so the previous week's summary is complete
- [x] #4 Hovering or pinning a weekly summary row highlights only activities in the week shown
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Serve activities since Monday 00:00 of the previous week from /api/status\n2. Make the report's week range derive from the displayed day instead of today\n3. Carry the week in hover/pin state so highlights match the week shown\n4. Unit-test the timeline start and the since cutoff; exercise the JS week logic with node
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The report panel's weekly section now follows the timeline: its range is the Mon–Sun week containing the day shown in the daily section (the topmost visible day), and its heading reads This Week / Last Week.

- /api/status serves activities since Monday 00:00 of the previous week (was a rolling 7 days), so the previous week's summary is complete; the timeline is 8–14 days long depending on the weekday.
- Hover/pin state for weekly rows carries the week shown, so highlights are limited to that week. A pinned weekly row stays tied to the week it was pinned in.
- _read_activities takes an explicit since datetime instead of a day count.
- JS week logic (week key, label, Sunday/Monday boundary, highlight matching) was exercised with node against the served script; Python side has unit tests.

Files: src/taskbridge/web_ui.py, tests/unit/test_web_ui.py
<!-- SECTION:NOTES:END -->
