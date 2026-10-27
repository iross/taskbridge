---
id: TASK-48
title: Add existing-tag picker to web UI start form and edit modal
status: Done
assignee:
  - '@claude'
created_date: '2026-10-16 18:47'
updated_date: '2026-10-16 18:48'
labels:
  - web-ui
  - time-tracking
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Tags live inside bartib descriptions as #tag tokens, so reusing one means remembering and retyping its exact spelling. A one-click way to add a previously used tag while starting or editing an entry keeps tags consistent and makes tagging fast enough to actually do.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The start form and the edit modal each show clickable chips for previously used tags beneath the Description field, most-used first
- [x] #2 Clicking a chip appends #tag to the description; clicking it again removes it
- [x] #3 Chips for tags already present in the description appear selected, and stay in sync as the description is typed or edited
- [x] #4 The tag list covers all tags in the bartib log plus tags with configured colors, not just the last 7 days
- [x] #5 Tags use their existing colors (configured or hashed), matching the chips shown on activities
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Backend: _read_tag_counts() over the full bartib log (reusing split_description_tags), merged with tag_colors keys; GET /api/tags returns names sorted by usage
2. Frontend: shared tag-picker renderer bound to an input id; toggleTagIn() adds/removes #tag; sync selected state on input events
3. Mount under start-form Description and edit-modal Description; reload tags after start/save
4. Tests for tag counting and the endpoint; ruff/ty/pytest; smoke test the page
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added a tag picker under the Description field in the start form and the edit modal.
- Backend: _read_tag_counts() counts #tags over the whole bartib log (reusing main.split_description_tags), and _known_tags() merges in configured tag_colors keys (case-insensitively, count 0) and sorts most-used first, then alphabetically. New GET /api/tags returns 500 with an error message if the log can't be read.
- Frontend: renderTagPicker(inputId) draws chips into <inputId>-tags, styled with the shared chipStyle() (factored out of tagChips so the picker and activity chips use the same colors); chips for tags present in the description get .on. toggleTagIn() appends or removes the #tag token. The picker re-renders on input events, and tags reload after starting or saving an entry so new tags appear. Chips use mousedown preventDefault so clicking doesn't steal focus from the field.
- Files: src/taskbridge/web_ui.py, tests/unit/test_web_ui.py (5 new tests). The JS toggle logic was checked ad hoc in node with a stubbed DOM; there's no JS test harness in the repo.
<!-- SECTION:NOTES:END -->
