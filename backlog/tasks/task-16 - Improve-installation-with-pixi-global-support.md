---
id: task-16
title: Improve installation with pixi global support
status: To Do
assignee:
  - '@iross'
created_date: '2025-08-22 16:40'
updated_date: '2025-08-22 16:41'
labels: []
dependencies: []
priority: medium
---

## Description

Simplify TaskBridge installation and Taskwarrior hook setup using pixi global install to eliminate Python path issues and make the tool easily installable across different environments

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 TaskBridge can be installed globally via 'pixi global install taskbridge',Hook script uses stable Python shebang that works across environments,Installation command automatically sets up Taskwarrior hook in ~/.task/hooks/,Hook script works from any directory without path issues,Installation includes all dependencies without manual setup,Uninstallation cleanly removes all components,Documentation provides simple one-command installation instructions,Works on macOS Linux and Windows where pixi is available
<!-- AC:END -->

## Implementation Plan

1. **Research pixi global packaging requirements**
   - Study pixi.toml format for global packages
   - Understand how pixi handles Python dependencies and shebangs
   - Research how other CLI tools handle global installation

2. **Create pixi package configuration**
   - Add pixi.toml to TaskBridge project root
   - Configure package metadata and dependencies
   - Set up proper entry points for CLI and hook script
   - Define platform-specific configurations if needed

3. **Update hook script for pixi compatibility**
   - Modify shebang to use pixi-managed Python
   - Test that hook works after pixi global install
   - Ensure script finds TaskBridge modules correctly
   - Add fallback logic for non-pixi environments

4. **Create installation CLI command**
   - Add 'taskbridge install-hook' command to CLI
   - Automatically copy hook to ~/.task/hooks/ with correct permissions
   - Validate Taskwarrior configuration exists
   - Provide clear success/error feedback

5. **Add uninstallation support**
   - Add 'taskbridge uninstall-hook' command
   - Remove hook script from ~/.task/hooks/
   - Clean up any configuration or log files
   - Provide confirmation of removal

6. **Update documentation**
   - Create simple installation guide using pixi
   - Update README with one-command install instructions
   - Add troubleshooting section for common issues
   - Document uninstallation process

7. **Test across environments**
   - Test on clean systems without existing Python setup
   - Verify works with different pixi versions
   - Test installation/uninstallation cycles
   - Validate hook functionality after pixi install
