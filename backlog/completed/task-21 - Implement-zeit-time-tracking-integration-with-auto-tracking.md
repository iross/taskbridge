---
id: task-21
title: Implement zeit time tracking integration with auto-tracking
status: Done
assignee:
  - '@claude'
created_date: '2026-01-08 20:04'
labels: []
dependencies:
  - task-19
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Integrate zeit time tracking into taskbridge with manual commands, auto-tracking on task actions, and Todoist integration
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Manual time start/stop/list/stats commands implemented
- [x] #2 Auto-tracking on task note creation implemented
- [x] #3 Auto-stop on task completion implemented
- [x] #4 Auto-switch between tasks implemented
- [x] #5 Todoist comments with tracked time implemented
- [x] #6 Project name sanitization for zeit implemented
- [x] #7 Database schema and CRUD operations implemented
- [x] #8 All features tested and working
<!-- AC:END -->

## Implementation Notes

### Overview
Successfully integrated zeit time tracking into taskbridge with full auto-tracking capabilities and Todoist integration.

### Features Implemented

**1. Manual Time Commands** (`src/taskbridge/main.py:1186-1397`)
- `taskbridge time start [--task TASK_ID] [--note NOTE]` - Start tracking with optional Todoist link
- `taskbridge time stop [--note NOTE]` - Stop tracking and log duration
- `taskbridge time list [--project] [--days]` - List time blocks with filtering
- `taskbridge time stats [--project] [--period]` - View time statistics

**2. Auto-Tracking** (`src/taskbridge/main.py:521-548`)
- Modified `task_note()` command to auto-start tracking when creating notes
- Stops any previous active tracking before starting new session
- Uses sanitized Todoist project names for zeit projects

**3. Auto-Stop** (`src/taskbridge/main.py:369-378`)
- Modified `task_done()` command to auto-stop tracking when completing tasks
- Calculates total duration and adds comment to Todoist
- Format: "⏱️ Tracked 2h 15m"

**4. Auto-Switch Logic**
- When starting tracking on a different task, automatically stops previous tracking
- Logs duration for stopped task
- Seamless transition between tasks

**5. Database Schema** (`src/taskbridge/database.py:34-46, 112-143`)
- Added `TaskTimeTracking` dataclass
- Created `task_time_tracking` table with indices
- CRUD methods: `create_tracking_record()`, `get_active_tracking()`, `get_tracking_by_task_id()`, `update_tracking_record()`

**6. Helper Functions** (`src/taskbridge/main.py:1148-1234`)
- `sanitize_project_name()` - Removes emojis, special chars, normalizes for zeit
- `format_duration()` - Formats seconds as "2h 15m"
- `calculate_duration()` - Calculates duration from zeit blocks
- `stop_tracking_internal()` - Centralized stop logic with Todoist comments

### Technical Decisions

1. **Project Name Sanitization**: Added regex-based sanitization to handle emojis and special characters in Todoist project names
2. **Database Tracking**: Store tracking records in SQLite for persistence and linking to Todoist tasks
3. **Error Handling**: Zeit failures don't block main task operations (warnings only)
4. **Generic Tracking**: Non-linked tracking uses default "taskbridge/general" project

### Modified Files
- `src/taskbridge/main.py` - Added time commands, auto-tracking, helper functions (~260 lines added)
- `src/taskbridge/database.py` - Added TaskTimeTracking model and methods (~160 lines added)
- `src/taskbridge/zeit_integration.py` - No changes (already complete from task-19)

### Testing Results
All scenarios tested successfully:
- ✅ Manual time start/stop with and without Todoist links
- ✅ Auto-tracking on note creation
- ✅ Auto-stop on task completion
- ✅ Auto-switch between tasks
- ✅ Duration calculation and formatting
- ✅ Todoist comments with tracked time
- ✅ Project name sanitization (handles emojis)

### Future Enhancements
- Add time reports and analytics
- Support for time entry editing
- Batch time tracking operations
- Integration with other time tracking services
