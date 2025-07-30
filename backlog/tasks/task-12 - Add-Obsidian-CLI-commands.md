---
id: task-12
title: Add Obsidian CLI commands
status: To Do
assignee: []
created_date: '2025-07-30'
labels:
  - obsidian
  - cli
dependencies:
  - task-10
  - task-11
priority: medium
---

## Description

Extend CLI interface with Obsidian-specific commands for note management and task linking

## Acceptance Criteria

- [ ] taskbridge note <task-id> creates or opens task-specific note
- [ ] taskbridge note --search <query> finds tasks and creates notes interactively
- [ ] Notes automatically linked when starting timers with taskbridge start
- [ ] taskbridge list-notes [client] [project] shows existing notes by project
- [ ] Commands handle missing Obsidian config gracefully with helpful messages
- [ ] Integration with existing search and start commands
