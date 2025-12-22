---
id: task-13
title: Implement project completion and archiving functionality
status: Done
assignee: []
created_date: '2025-08-13'
updated_date: '2025-12-22 21:34'
labels:
  - feature
  - project-management
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add comprehensive project lifecycle management to handle completed projects, including archiving workflows, status transitions, and cleanup processes to maintain system organization and performance
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Users can mark projects as completed
- [ ] #2 Completed projects are properly archived with all associated data
- [ ] #3 Archive functionality preserves project history and accessibility
- [ ] #4 System provides clear workflows for project completion process
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented archiving functionality:
- `taskbridge task done` command marks tasks complete in Todoist and archives notes by default
- `taskbridge project archive` moves entire project folders to "40 Archive"
- Database mappings updated automatically when notes are archived
- Note frontmatter status set to "done" on archival

Files modified:
- src/taskbridge/main.py (task done and project archive commands)
- src/taskbridge/todoist_api.py (added close_task method)
<!-- SECTION:NOTES:END -->
