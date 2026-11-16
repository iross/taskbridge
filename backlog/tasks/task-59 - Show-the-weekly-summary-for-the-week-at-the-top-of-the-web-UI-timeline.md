---
id: TASK-59
title: Show the weekly summary for the week at the top of the web UI timeline
status: In Progress
assignee: []
created_date: '2026-11-16 16:05'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The web UI report panel always summarises the current week, even when the timeline is scrolled back to days from the previous week. On a Monday the weekly summary is nearly empty while the timeline shows mostly last week. The weekly summary should follow the timeline the same way the daily summary already does.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Weekly summary covers the Mon–Sun week containing the topmost visible day of the timeline,Weekly summary heading names the week shown (This Week / Last Week),Timeline reaches back to the Monday of the previous week so the previous week's summary is complete,Hovering or pinning a weekly summary row highlights only activities in the week shown
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Serve activities since Monday 00:00 of the previous week from /api/status\n2. Make the report's week range derive from the displayed day instead of today\n3. Carry the week in hover/pin state so highlights match the week shown\n4. Unit-test the timeline start and the since cutoff; exercise the JS week logic with node
<!-- SECTION:PLAN:END -->
