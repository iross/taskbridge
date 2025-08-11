---
id: task-07
title: Implement complete CLI interface
status: To Do
assignee: []
created_date: '2025-07-30'
labels:
  - cli
  - interface
dependencies: []
priority: high
---

## Description

Build the full command-line interface with all required commands for TaskBridge functionality

## Acceptance Criteria

- [ ] All commands implemented: config
- [ ] sync
- [ ] search
- [ ] start
- [ ] status
- [ ] stop
- [ ] list-projects
- [ ] Search command displays Linear issues with interactive selection
- [ ] Start command supports both direct task ID and interactive search fallback
- [ ] Auto-stops current timer when starting new ones
- [ ] Status command shows detailed current timer information
- [ ] Stop command ends current timer and confirms action
- [ ] List-projects command displays current project mappings
- [ ] Command-line arguments and options handled properly with typer
