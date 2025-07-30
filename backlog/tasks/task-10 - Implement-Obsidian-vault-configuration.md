---
id: task-10
title: Implement Obsidian vault configuration
status: To Do
assignee: []
created_date: '2025-07-30'
labels:
  - obsidian
  - config
dependencies: []
priority: medium
---

## Description

Add configuration support for Obsidian vault path and note organization settings to enable task-specific note creation

## Acceptance Criteria

- [ ] Config supports obsidian_vault_path setting in ~/.taskbridge/config.yaml
- [ ] Config supports obsidian_notes_folder setting (default: TaskBridge Notes)
- [ ] Interactive config command prompts for Obsidian vault location
- [ ] Vault path validation ensures directory exists and is writable
- [ ] Config validates vault contains .obsidian folder to confirm it's an Obsidian vault
- [ ] Settings are optional - TaskBridge works without Obsidian integration
