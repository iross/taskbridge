---
id: task-11
title: Create task note generation system
status: To Do
assignee: []
created_date: '2025-07-30'
labels:
  - obsidian
  - notes
dependencies:
  - task-10
priority: medium
---

## Description

Build functionality to create structured task-specific notes in Obsidian with proper frontmatter and project organization

## Acceptance Criteria

- [ ] Notes created in vault_path/notes_folder/Client/Project/ directory structure
- [ ] Note filename format: YYYY-MM-DD - Task Name.md
- [ ] Frontmatter includes: client project linear_issue_id toggl_project_id created_date task_url
- [ ] Note body template includes task description and empty sections for notes/progress
- [ ] Automatic folder creation for new Client/Project combinations
- [ ] Integration with existing project mappings from sync engine
