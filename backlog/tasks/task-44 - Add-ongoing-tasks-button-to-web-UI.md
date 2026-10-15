---
id: TASK-44
title: Add ongoing tasks button to web UI
status: To Do
assignee: []
created_date: '2026-10-15 15:58'
labels:
  - time-tracking
  - web-ui
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Some work never closes: email, catchup after an outage or travel, morning focus. Today these get tracked as ad-hoc entries with inconsistent projects (e.g. "Email, task management" was logged under Other::Other, CHTC, chtc, and CHTC::Other). An Ongoing button gives these saved definitions and one-click start, the same way saved meetings work, with no Todoist task needed. It is only for generic, ambient work; anything tied to a specific subject (which PR, which group, which report change) stays a Todoist task. Replaces the Todoist-label-backed approach previously planned in TASK-28.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An '∞ Ongoing' button sits in the web UI toolbar next to the Meeting button and opens a dropdown of saved ongoing items, most-used first
- [ ] #2 Picking an item stops any active tracking and starts bartib with the item's description and client::project, adding an #ongoing tag
- [ ] #3 New ongoing items (alias, description, project, client, tags) can be defined, and existing ones removed, from inside the dropdown
- [ ] #4 Definitions persist in ~/.taskbridge/config.yaml under a separate 'ongoing' key, not mixed in with meetings
- [ ] #5 The button shows an active state while an ongoing item is being tracked
- [ ] #6 'taskbridge ongoing define|list|undefine|start' provides the same capabilities from the CLI
- [ ] #7 Ongoing entries stop and report like any other tracked activity, and no Todoist task is required
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Suggested starting items (from bartib history Feb-Oct 2026; add via the feature once shipped, not in code):
- email: 'Email & task management' -> CHTC::Other (13 entries Jun-Sep under 4 different projects)
- focus: 'Morning focus' -> CHTC::Other (17+ entries; project drifted between Other, Inbox, CHTC)
- catchup: 'Post-outage / post-travel catchup' -> CHTC::Other (9/9, 9/22, 10/12, plus post-school catchup 7/20)
Excluded: code review, user consults, GPU reporting (subject-specific -> Todoist tasks); hiring reviews (seasonal); standups/staff meetings (already saved meetings).
<!-- SECTION:NOTES:END -->
