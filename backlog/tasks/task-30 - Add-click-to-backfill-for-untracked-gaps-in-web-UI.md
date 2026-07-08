---
id: TASK-30
title: Add click-to-backfill for untracked gaps in web UI
status: To Do
assignee: []
created_date: '2026-07-07 16:34'
updated_date: '2026-07-07 16:34'
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
- [ ] #1 Clicking a gap indicator opens the existing log/start form prefilled with the gap's start and end times
- [ ] #2 User can adjust times and pick a project/task before saving
- [ ] #3 Submitting creates a bartib entry covering the gap and refreshes the timeline so the gap shrinks or disappears
- [ ] #4 Gaps remain non-interactive for the currently running activity's open end
<!-- AC:END -->
