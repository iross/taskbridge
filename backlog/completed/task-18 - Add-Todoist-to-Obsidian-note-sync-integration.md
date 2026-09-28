---
id: task-18
title: Add Todoist to Obsidian note sync integration
status: Done
assignee: []
created_date: '2025-12-17 21:26'
updated_date: '2025-12-17 21:35'
labels:
  - todoist
  - obsidian
  - integration
  - sync
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Enable seamless note-taking workflow where Todoist tasks can trigger Obsidian note creation with automatic bidirectional linking. Currently using Todoist for task tracking and Obsidian for detailed notes, but the linking is manual. This integration will allow one-click note creation from Todoist tasks, with the Obsidian URL automatically added back to the Todoist task as a comment for easy reference.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Todoist API client created with support for fetching projects, tasks, and creating comments
- [x] #2 Configuration command `config-todoist` allows interactive setup of API token, sync label, and project→folder mappings
- [x] #3 Command `create-todoist-note [task-id]` creates Obsidian note and adds URL as Todoist comment
- [x] #4 Command `sync-todoist-notes` batch processes all tasks with configured label (e.g., @obsidian)
- [x] #5 Project mappings support client metadata stored in config.yaml
- [x] #6 Database tracks synced tasks to prevent duplicates
- [x] #7 Notes use existing Obsidian template system and are created in correct project folders
- [x] #8 Obsidian URLs open correctly from Todoist comments
- [x] #9 Dry-run mode works for batch sync command
- [x] #10 Error handling for missing mappings, network failures, and duplicate notes

- [x] #11 Command `create-project` creates project in both Todoist and Obsidian, sets up folder structure, triggers project overview template, and saves mapping
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Implementation Summary

Successfully implemented complete Todoist→Obsidian integration for taskbridge.

### Files Created
- **src/taskbridge/todoist_api.py** (348 lines) - Complete REST API v2 client
  - TodoistProject and TodoistTask dataclasses
  - TodoistAPI class with Bearer token authentication
  - Methods: get_projects(), get_project(), create_project(), get_tasks(), get_task(), create_comment(), update_task(), validate_token()

### Files Modified
- **src/taskbridge/config.py** - Added Todoist configuration methods
  - get_todoist_token(), get_todoist_sync_label()
  - get_todoist_project_mappings(), set_todoist_project_mapping()
  - validate_todoist_token()

- **src/taskbridge/database.py** - Added Todoist note tracking
  - TodoistNoteMapping dataclass
  - todoist_notes table with indexes
  - CRUD methods: create_todoist_note_mapping(), get_todoist_note_by_task_id(), get_all_todoist_mappings(), update_todoist_note_mapping()

- **src/taskbridge/main.py** - Added four new CLI commands (358 lines)
  - **config-todoist**: Interactive setup for API token, sync label, and project mappings
  - **create-project**: Creates project in both Todoist and Obsidian, sets up folders, saves mappings
  - **create-todoist-note**: Creates Obsidian note for single task, adds URL as Todoist comment
  - **sync-todoist-notes**: Batch syncs all tasks with specified label

### Key Features Implemented
1. ✅ Bearer token authentication with validation
2. ✅ Project mapping config (Todoist project ID → Obsidian folder + client name)
3. ✅ Database tracking to prevent duplicate note creation
4. ✅ Automatic bidirectional linking (Obsidian URL added as Todoist comment)
5. ✅ Dry-run mode for batch sync
6. ✅ Reuses existing Obsidian infrastructure (templates, frontmatter, URL generation)
7. ✅ Error handling for missing mappings, network failures, invalid IDs
8. ✅ Interactive and flag-based command interfaces

### Technical Details
- API Base URL: https://api.todoist.com/rest/v2
- Authentication: Bearer token in Authorization header
- Database: SQLite table `todoist_notes` with task_id and project_id indexes
- Config storage: YAML at ~/.taskbridge/config.yaml
- Obsidian URL format: obsidian://open?vault={name}&file={path}

### Configuration Example
```yaml
todoist_token: "YOUR_API_TOKEN"
todoist_sync_label: "@obsidian"
todoist_project_mappings:
  "project-id-123":
    client: "Acme Corp"
    folder: "Acme Projects"
```

All syntax checks passed successfully. Implementation follows established patterns from Linear and Google Calendar integrations.
<!-- SECTION:NOTES:END -->
