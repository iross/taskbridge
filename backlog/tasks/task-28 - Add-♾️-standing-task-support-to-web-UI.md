---
id: TASK-28
title: Add ♾️ standing task support to web UI
status: To Do
assignee: []
created_date: '2026-06-17 13:42'
labels: []
dependencies:
  - TASK-27
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Standing tasks (Todoist tasks labelled ♾️) serve as time-tracking anchors for ambient background work. The web interface should make it as easy to start tracking against a standing task as it currently is to start a meeting — with a dedicated button, a quick-select dropdown populated from Todoist, and an inline form to create new standing tasks without leaving the UI.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] A `♾️ Standing` button appears in the web UI toolbar alongside the existing Meeting button
- [ ] Clicking the button opens a dropdown listing all Todoist tasks with the `♾️` label, fetched via the existing API
- [ ] Selecting a standing task from the dropdown starts time tracking against it (same flow as selecting a saved meeting)
- [ ] The dropdown includes an inline form to create a new standing task in Todoist with the `♾️` label applied, without leaving the UI
- [ ] The button shows an active/highlighted state while a standing task is being tracked
<!-- AC:END -->
