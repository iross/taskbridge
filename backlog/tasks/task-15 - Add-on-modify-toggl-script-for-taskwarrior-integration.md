---
id: task-15
title: Add on-modify toggl script for taskwarrior integration
status: To Do
assignee: []
created_date: '2025-08-22 13:27'
labels: []
dependencies: []
---

## Description

Create a Taskwarrior on-modify hook script that automatically integrates with Toggl for time tracking. This script will monitor Taskwarrior task events and start/stop Toggl timers accordingly, parsing client information from task tags to set appropriate Toggl client and project associations.

## Acceptance Criteria

- [ ] Script automatically starts Toggl timer when a Taskwarrior task is started
- [ ] Script extracts client name from `client:xyz` tag format in task tags
- [ ] Script maps client name to existing Toggl client or creates new one if needed
- [ ] Script sets Toggl project appropriately based on task project (filtering out client names if present)
- [ ] Script maps project name to existing Toggl project or creates new one if needed
- [ ] Script automatically stops Toggl timer when task is completed or stopped
- [ ] Script reports total time spent on the task after stopping
- [ ] Script reports total project time accumulated so far after stopping.
- [ ] Script handles edge cases (no client tag, invalid client, API errors) gracefully
- [ ] Script follows Taskwarrior hook conventions and outputs modified task JSON
- [ ] Script is properly documented with usage instructions

## Implementation Plan

1. **Research and Setup**
   - Study the existing Timewarrior hook (`/opt/homebrew/share/doc/timew/ext/on-modify.timewarrior`) as reference
   - Review Taskwarrior hook documentation and JSON format specifications
   - Analyze existing TaskBridge Toggl API client capabilities

2. **Core Hook Structure**
   - Create Python script following Taskwarrior hook conventions
   - Implement JSON parsing for old/new task states from stdin
   - Add proper error handling and logging framework
   - Ensure script outputs modified task JSON as required

3. **Task State Detection**
   - Implement logic to detect task start events (`start` in new, not in old)
   - Implement logic to detect task stop/completion events (`start` not in new or `end` in new, but `start` in old)
   - Handle task modification events (changes to running tasks)

4. **Client and Project Resolution**
   - Parse `client:xyz` tags from task tags array
   - Integrate with existing TaskBridge Toggl API to find/create clients
   - Implement project resolution logic (use task project or create default)
   - Add fallback handling for tasks without client tags

5. **Toggl Timer Management**
   - Integrate with existing `TogglAPI.start_timer()` method
   - Integrate with existing `TogglAPI.stop_timer()` method
   - Handle timer conflicts and cleanup properly

6. **Reporting and Feedback**
   - Calculate and report individual task time on completion
   - Query and report total project time accumulation
   - Provide user-friendly console output with time summaries

7. **Testing and Installation**
   - Test script with various Taskwarrior scenarios
   - Create installation instructions for hook placement
   - Add configuration requirements documentation
