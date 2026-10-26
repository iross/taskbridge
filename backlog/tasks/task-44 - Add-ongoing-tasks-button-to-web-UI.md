---
id: TASK-44
title: Add ongoing tasks button to web UI
status: Done
assignee:
  - '@claude'
created_date: '2026-10-15 15:58'
updated_date: '2026-10-15 16:05'
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
- [x] #1 An '∞ Ongoing' button sits in the web UI toolbar next to the Meeting button and opens a dropdown of saved ongoing items, most-used first
- [x] #2 Picking an item stops any active tracking and starts bartib with the item's description and client::project, adding an #ongoing tag
- [x] #3 New ongoing items (alias, description, project, client, tags) can be defined, and existing ones removed, from inside the dropdown
- [x] #4 Definitions persist in ~/.taskbridge/config.yaml under a separate 'ongoing' key, not mixed in with meetings
- [x] #5 The button shows an active state while an ongoing item is being tracked
- [x] #6 'taskbridge ongoing define|list|undefine|start' provides the same capabilities from the CLI
- [x] #7 Ongoing entries stop and report like any other tracked activity, and no Todoist task is required
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a single synthetic-task-ID check (meeting:/cal:/ongoing:) and use it everywhere the code currently checks 'meeting:' prefixes
2. Factor Config meeting template storage into shared helpers; add ongoing get/set/delete/usage
3. Web API: generalize meeting list/start/define/undefine handlers by template kind; add /api/ongoing routes
4. Web UI: ∞ Ongoing button + dropdown reusing meeting dropdown markup; parameterize JS by kind; active state from current tracking's task id
5. CLI: taskbridge ongoing define|list|undefine|start, sharing the tracking-switch logic with meeting start
6. Tests for config, CLI, web handlers, and synthetic ID check; ruff + ty + pytest
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Suggested starting items (from bartib history Feb-Oct 2026; add via the feature once shipped, not in code):
- email: 'Email & task management' -> CHTC::Other (13 entries Jun-Sep under 4 different projects)
- focus: 'Morning focus' -> CHTC::Other (17+ entries; project drifted between Other, Inbox, CHTC)
- catchup: 'Post-outage / post-travel catchup' -> CHTC::Other (9/9, 9/22, 10/12, plus post-school catchup 7/20)
Excluded: code review, user consults, GPU reporting (subject-specific -> Todoist tasks); hiring reviews (seasonal); standups/staff meetings (already saved meetings).

Implementation:
- Config: replaced the meeting-specific get/set/delete/usage methods with one API keyed by template kind (get_templates, set_template, delete_template, get_template_usage, increment_template_usage). TEMPLATE_KINDS in config.py defines each kind's config key, usage key, default project, auto-tag and noun. Ongoing items live under the 'ongoing' key, usage under 'ongoing_usage'.
- Synthetic IDs: added is_real_todoist_task_id() in database.py covering meeting:, cal: and ongoing: prefixes. It replaces the eight hand-written prefix checks in web_ui.py and main.py. Side effect: cal: entries no longer trigger a Todoist comment attempt on stop, or Todoist note/complete actions.
- Web: the meeting list/start/define/undefine handlers are now generic by kind. New routes: GET /api/ongoing and POST /api/ongoing/{start,define,undefine}. Ongoing starts record todoist_task_id 'ongoing:<slug>' and auto-tag #ongoing, with project defaulting to 'ongoing'.
- UI: an '∞ Ongoing' button and dropdown sit next to Meeting, reusing the meeting dropdown styles with a new --ongoing color. The dropdown JS is parameterized by kind. The button highlights when the current tracking's task id starts with 'ongoing:'.
- CLI: 'taskbridge ongoing define|list|undefine|start'. 'start' requires a defined alias (no ad-hoc mode). switch_tracking_to_synthetic() is shared with 'meeting start'.
- Files: config.py, database.py, main.py, web_ui.py, tests/unit/test_meetings.py (migrated to the generic API), tests/unit/test_ongoing.py (new, 34 tests).
<!-- SECTION:NOTES:END -->
