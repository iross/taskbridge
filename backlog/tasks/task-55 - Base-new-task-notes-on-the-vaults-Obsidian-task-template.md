---
id: TASK-55
title: Base new task notes on the vault's Obsidian task template
status: Done
assignee:
  - '@claude'
created_date: '2026-11-03 20:19'
updated_date: '2026-11-03 20:20'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Task notes created by taskbridge drift from the ones made by the vault's templates/task.md: project is written as plain text instead of the wikilink Metadata Menu's File field expects, and fixed keys like obsidianEditingMode are missing. New notes should take their fixed frontmatter from the template so the two stay in step.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 New task notes carry the template's fixed frontmatter keys exactly as written there
- [x] #2 project is written as a [[wikilink]] to the project note
- [x] #3 status/client/tags come from the Todoist task and due is left empty
- [x] #4 No title heading or template body is written into the note
- [x] #5 A missing template falls back to fileClass: task and a malformed one fails with an error naming the file
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a scalar setter to the frontmatter module alongside set_list
2. Seed create_task_note from templates/task.md frontmatter, then set project/status/client/due/tags
3. Unit-test template copy, overrides, missing and malformed template, existing note
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- create_task_note (config.py) copies the frontmatter lines of <vault>/templates/task.md (TASK_TEMPLATE) verbatim, then sets project ('[[<last path segment>]]', matching the template's proj.split('/').pop()), status, client, due ('') and tags (block list). The Templater script body is not copied and the '# <title>' heading is gone, so the note body is empty.
- Missing template falls back to 'fileClass: task'; malformed template frontmatter raises ValueError naming the file.
- frontmatter.py: added set_value; set_list and set_value share _replace so untouched template lines keep their formatting.
- Deliberately ties taskbridge to this vault's layout (templates/task.md).
- Files: src/taskbridge/config.py, src/taskbridge/frontmatter.py, tests/unit/test_config.py, tests/unit/test_frontmatter.py
<!-- SECTION:NOTES:END -->
