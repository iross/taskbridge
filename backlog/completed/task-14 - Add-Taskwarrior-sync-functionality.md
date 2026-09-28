---
id: task-14
title: Add Taskwarrior sync functionality
status: Done
assignee:
  - '@claude'
created_date: '2025-08-19 15:44'
updated_date: '2025-08-19 18:14'
labels: []
dependencies: []
---

## Description

Enable bidirectional synchronization between the task management system and Taskwarrior to allow users to manage tasks using Taskwarrior's CLI interface

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Can export tasks to Taskwarrior format,Can import tasks from Taskwarrior,Sync preserves task relationships and metadata,Configuration options for sync behavior
<!-- AC:END -->

## Implementation Plan

1. Research Taskwarrior CLI interface and data format\n2. Design Taskwarrior API wrapper class\n3. Implement TaskwarriorProvider following the existing provider schema\n4. Add CLI commands for Taskwarrior sync operations\n5. Add configuration support for Taskwarrior\n6. Test bidirectional synchronization\n7. Update documentation

## Implementation Notes

Successfully implemented Taskwarrior sync functionality with the following features:\n\n**Core Components:**\n- TaskWarriorAPI: Custom CLI wrapper for taskwarrior export/import\n- TaskwarriorProvider: Provider interface implementation following schema\n- CLI commands: tw-projects, tw-tasks, tw-export, tw-create, tw-complete, tw-sync\n- Configuration support: taskwarrior command path and enable/disable toggle\n\n**Features Implemented:**\n- Bidirectional task data conversion (TaskWarrior <-> Universal format)\n- Project and task listing with filtering\n- Task creation with projects, priorities, and tags\n- Task completion functionality\n- JSON export capabilities\n- Configuration management\n\n**Files Created:**\n- src/taskbridge/taskwarrior_api.py\n- src/taskbridge/taskwarrior_provider.py\n\n**Files Modified:**\n- src/taskbridge/main.py (added CLI commands)\n- src/taskbridge/config.py (added Taskwarrior config methods)\n\n**Technical Approach:**\n- Used subprocess calls to taskwarrior CLI\n- JSON export/import for data exchange\n- Python-side filtering due to taskwarrior query limitations\n- Universal provider schema for cross-system compatibility

Successfully implemented complete Taskwarrior sync functionality with enhanced features:

**Core Components:**
- TaskWarriorAPI: Custom CLI wrapper using taskwarrior export/import
- TaskwarriorProvider: Universal provider interface implementation
- CLI commands: tw-projects, tw-tasks, tw-export, tw-create, tw-complete, tw-sync, sync-linear-to-tw
- Configuration: config-taskwarrior command with enable/disable toggle

**Key Features Implemented:**
- ✅ Bidirectional task data conversion (TaskWarrior ↔ Universal format)
- ✅ Client mapping using Linear project labels (#client/CLIENT_NAME format)
- ✅ Project naming: Client.Project format (e.g., CHTC.Other, PATh.Evaluations)
- ✅ Client tags: client:CLIENT_NAME for easy filtering
- ✅ Linear ID tracking: Moved to annotations (Linear ID: xxxxx) instead of tags
- ✅ System tag: _linear (underscore prefix following Taskwarrior conventions)
- ✅ Obsidian URL sync: Searches both Linear descriptions AND comments
- ✅ Duplicate prevention: Smart detection via annotations and titles
- ✅ JSON export capabilities
- ✅ Task creation, completion, and management

**Enhanced Obsidian Integration:**
- Searches Linear issue descriptions for obsidian:// URLs
- Searches Linear issue comments for obsidian:// URLs
- Adds found URLs as Taskwarrior annotations with 📝 prefix
- Preserves comment timestamps for annotation entries

**Files Created:**
- src/taskbridge/taskwarrior_api.py (280+ lines)
- src/taskbridge/taskwarrior_provider.py (350+ lines)

**Files Modified:**
- src/taskbridge/main.py (added CLI commands and sync logic)
- src/taskbridge/config.py (added Taskwarrior configuration methods)
- src/taskbridge/linear_api.py (added get_issue_comments method)

**Technical Decisions:**
- Used subprocess calls to taskwarrior CLI for reliability
- JSON export/import for data exchange
- Python-side filtering due to taskwarrior query syntax limitations
- Annotation-based Linear ID storage for cleaner tags
- Universal provider schema for cross-system compatibility
- Comment searching via Linear GraphQL API for complete Obsidian URL discovery

**Testing Results:**
- ✅ All CLI commands functional
- ✅ Client mapping working (CHTC.Other, PATh.Evaluations)
- ✅ Linear ID annotations properly created
- ✅ Obsidian URLs found in both descriptions and comments
- ✅ Deduplication preventing double-syncing
- ✅ Task completion and management working
- ✅ Project statistics and filtering functional

The implementation provides a robust, production-ready Taskwarrior integration that maintains full traceability between Linear and Taskwarrior while preserving all metadata including client relationships and Obsidian note links.
