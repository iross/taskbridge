---
id: TASK-41
title: Add notebook-sweep and daily-top-3 standing tasks to Todoist
status: To Do
assignee: []
created_date: '2026-08-07 18:59'
labels: []
dependencies:
  - TASK-27
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two handwriting-adjacent rituals should exist as always-present standing tasks once task-27 lands: (1) 'Sweep the notebook' - periodically review handwritten notes and transcribe anything actionable into Todoist/Obsidian, and (2) 'Write down today's top 3 and flag the top one as priority in Todoist' - a daily habit of setting focus on paper first, then reflecting it into Todoist. These are deliberately manual rituals, not automation - taskbridge's only role is hosting them as recurring anchors via the standing-task mechanism, not reading or processing notebook content itself.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 'Sweep the notebook' exists in Todoist with the standing-task label and a weekly recurrence,'Write today's top 3 + flag top priority' exists in Todoist with the standing-task label and a daily recurrence,No taskbridge code changes beyond what task-27 already provides - this is about creating the Todoist items themselves, not new adapters or scanners,Both tasks appear correctly when filtering to standing tasks via the mechanism task-27 establishes
<!-- AC:END -->
