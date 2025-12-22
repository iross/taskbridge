---
id: task-12
title: Add Obsidian CLI commands
status: Done
assignee: []
created_date: '2025-07-30'
updated_date: '2025-12-22 21:34'
labels:
  - obsidian
  - cli
dependencies:
  - task-10
  - task-11
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend CLI interface with Obsidian-specific commands for note management and task linking
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 taskbridge note <task-id> creates or opens task-specific note
- [ ] #2 taskbridge note --search <query> finds tasks and creates notes interactively
- [ ] #3 Notes automatically linked when starting timers with taskbridge start
- [ ] #4 taskbridge list-notes [client] [project] shows existing notes by project
- [ ] #5 Commands handle missing Obsidian config gracefully with helpful messages
- [ ] #6 Integration with existing search and start commands
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented comprehensive CLI with noun-verb pattern:
- `taskbridge config` (todoist, obsidian configuration)
- `taskbridge task` (list, show, note, done)
- `taskbridge project` (list, create, archive)
- `taskbridge map` (list, show, update)
- `taskbridge sync` (notes, projects)

Complete CLI restructure from flat command structure to organized command groups using Typer.

Files modified:
- src/taskbridge/main.py (complete rewrite with command groups)
<!-- SECTION:NOTES:END -->
