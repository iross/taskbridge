---
id: TASK-25
title: Build web UI for bartib time log
status: Done
assignee: []
created_date: '2026-05-20 20:18'
updated_date: '2026-05-20 20:47'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a lightweight local web interface for viewing and managing time tracking data. The bartib file is the source of truth (plaintext log); the UI should render it in a readable way and provide shortcuts to start/stop tracking using projects pulled from Todoist and tasks from the existing taskbridge integrations — reducing friction compared to the CLI.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Web server starts via a taskbridge CLI command (e.g. `taskbridge time serve`)
- [x] #2 Bartib activity log is rendered in the browser with clear start/end times and project labels
- [x] #3 Currently running activity (if any) is highlighted and shows elapsed time
- [x] #4 User can start a new activity by selecting a project from a dropdown populated from Todoist projects
- [x] #5 User can select a recent or active Todoist task as the activity description
- [x] #6 User can stop the current activity with a single button click
- [x] #7 Recent activities list refreshes automatically (poll or SSE) without a full page reload
- [x] #8 No external JS framework dependencies — plain HTML/CSS/JS or minimal server-side rendering
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create src/taskbridge/web_ui.py with HTTP server, API endpoints, and embedded HTML/CSS/JS\n2. Add taskbridge time serve command to main.py (lazy import to avoid circular deps)\n3. Endpoints: GET / (HTML), GET /api/status (current + activities), GET /api/projects (Todoist + recent bartib), GET /api/tasks?project_id=X, POST /api/start, POST /api/stop\n4. JS polls /api/status every 10s; client-side 1s timer updates elapsed display\n5. Project dropdown: Todoist projects (optgroup) + recent bartib projects (optgroup)\n6. When project selected, fetch tasks for that project and populate description datalist
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Created src/taskbridge/web_ui.py (~360 lines) with a stdlib-only HTTPServer exposing six endpoints (GET /, /api/status, /api/projects, /api/tasks; POST /api/start, /api/stop). The HTML page is embedded as a module-level string with inline CSS (dark/light mode via prefers-color-scheme) and vanilla JS polling every 10s plus a client-side 1s elapsed timer. Added taskbridge time serve command to main.py using a lazy import to avoid circular dependency. Project dropdown shows Todoist projects (optgroup) and recent bartib projects (optgroup); selecting a Todoist project fetches its tasks to populate the description datalist. Stop action mirrors stop_tracking_internal logic (updates DB + Todoist comment). No new package dependencies.
<!-- SECTION:NOTES:END -->
