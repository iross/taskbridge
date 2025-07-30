---
id: task-06
title: Implement project synchronization engine
status: To Do
assignee: []
created_date: '2025-07-30'
labels:
  - sync
  - core-logic
dependencies: []
priority: high
---

## Description

Build the core sync logic to maintain project mappings between Todoist and Toggl with preview and user confirmation

## Acceptance Criteria

- [ ] Parses Todoist projects to extract Client/Project structure from #Client/Project format
- [ ] Compares existing mappings with current API state and identifies changes
- [ ] Generates preview of all changes (creates
- [ ] conflicts
- [ ] edge cases) before execution
- [ ] Handles projects not following #Client/Project pattern by showing them for user decision
- [ ] Updates database mappings after user confirms changes
- [ ] Supports bidirectional project creation between Todoist and Toggl
