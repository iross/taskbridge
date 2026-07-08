---
id: TASK-31
title: Store tags in bartib description instead of project path
status: Done
assignee:
  - '@claude'
created_date: '2026-07-07 16:34'
updated_date: '2026-07-08 14:57'
labels:
  - time-tracking
  - refactor
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Tags are currently string-joined into the bartib project path as a third segment (client/project/tag1,tag2). The same project tracked with different tags becomes different bartib projects, fragmenting reports, and tags cannot be queried or aggregated independently. Moving tags into the entry description as #tag tokens keeps bartib as the single source of truth, keeps project names clean, and makes tag-based filtering and reporting possible later.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 New entries store tags as #tag tokens in the bartib description and the project path contains only client/project
- [x] #2 Meeting definitions with tags produce clean project names with tags in the description
- [x] #3 Timeline and report views parse #tag tokens out of descriptions and display them separately from the description text
- [x] #4 Entries without tags behave exactly as before
- [x] #5 Existing bartib file entries are migrated in place: tag path segments become #tag description tokens (user has a backup)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. main.py: drop tags param from build_bartib_project; add append_tags_to_description() and split_description_tags() helpers
2. main.py call sites (task note auto-start, time start --task, meeting define/list/start): pass tags into the description instead of the project path
3. main.py build_report_entries: parse #tags from task_name, union with legacy tags from parse_project_segments (DB records are not migrated), report the cleaned description
4. web_ui.py: drop tags param from _build_bartib_project; _handle_start appends #meeting to description instead of ::meeting to project; _handle_meeting_start same
5. web_ui.py JS: parseTags() helper; timeline rows show clean description + tag chips; renderReport aggregates labels from description tags instead of project segments; edit modal keeps raw description so tags stay editable as text
6. One-off migration script (scratchpad): rewrite $BARTIB_FILE moving third :: segment into #tag tokens; dry-run diff before writing
7. Update unit tests (test_time_tracking, test_report), run pytest + ruff + ty
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Tags now live in bartib descriptions as #tag tokens; project paths are client::project only.

Approach:
- main.py: build_bartib_project() lost its tags param; new helpers append_tags_to_description() (sanitizes, dedupes against tags already present) and split_description_tags() (extracts whitespace-delimited #tag tokens, ignores bare '#')
- Producers updated to put tags in the description: task note auto-start, time start --task, meeting start (CLI + web), web _handle_start (is_meeting now appends #meeting instead of ::meeting)
- build_report_entries() unions tags parsed from the description with legacy tags from parse_project_segments(), so un-migrated DB records still report correctly; reported descriptions are cleaned
- Web UI JS: parseTags()/tagChips() render clean descriptions with tag chips in the timeline and current card; daily report panel aggregates labels from description tags instead of project segments; edit modal intentionally shows the raw description so tags stay editable as text
- Migrated the live bartib file (backup existed): 95 tag-segment entries plus 3 legacy 'meetings::meeting' ad-hoc lines rewritten to '... #meeting'. bartib check errors are unchanged pre-existing complaints about comment headers and blank lines

Trade-offs: DB records were not migrated (legacy parser covers them); tag parsing is duplicated in JS because the frontend renders raw bartib lines.

Files: src/taskbridge/main.py, src/taskbridge/web_ui.py, tests/unit/test_time_tracking.py, tests/unit/test_report.py, tests/unit/test_meetings.py. 180 tests pass; ruff and ty clean.
<!-- SECTION:NOTES:END -->
