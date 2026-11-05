---
id: TASK-41
title: Add notebook-sweep and daily-top-3 standing tasks to Todoist
status: Done
assignee: []
created_date: '2026-08-07 18:59'
updated_date: '2026-11-05 14:54'
labels: []
dependencies: []
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two handwriting-adjacent rituals should exist as always-present standing tasks once task-27 lands: (1) 'Sweep the notebook' - periodically review handwritten notes and transcribe anything actionable into Todoist/Obsidian, and (2) 'Write down today's top 3 and flag the top one as priority in Todoist' - a daily habit of setting focus on paper first, then reflecting it into Todoist. These are deliberately manual rituals, not automation - taskbridge's only role is hosting them as recurring anchors via the standing-task mechanism, not reading or processing notebook content itself.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 'Sweep the notebook' is available as an ongoing item to track time against
- [x] #2 'Write down today's top 3' is available as an ongoing item to track time against
- [x] #3 No taskbridge code changes
<!-- AC:END -->













## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Done via the existing ongoing mechanism rather than task-27's ♾️ label: 'taskbridge ongoing define notebook -d "Sweep the notebook"' and 'ongoing define top3 -d "Write down today's top 3"', both CHTC::Other like the other ongoing items. Configuration only, no code change.
<!-- SECTION:NOTES:END -->
