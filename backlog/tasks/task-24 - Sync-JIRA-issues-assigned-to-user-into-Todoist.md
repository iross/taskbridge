---
id: task-24
title: Sync JIRA issues assigned to user into Todoist
status: Done
assignee:
  - '@iross'
created_date: '2026-04-24 15:32'
updated_date: '2026-04-24 15:50'
labels:
  - jira
  - todoist
  - sync
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Enable users to pull Jira issues assigned to them and create corresponding Todoist tasks, making it easy to track Jira work within the existing taskbridge/Todoist workflow.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Running 'taskbridge sync jira' fetches all open Jira issues assigned to the configured user,Each fetched Jira issue is created as a Todoist task (with title and Jira URL in description) if it does not already exist,Re-running the command does not create duplicate Todoist tasks for already-synced issues,Jira connection config (base URL, user email, API token) is stored via 'taskbridge config jira' with the same UX as other config commands,Sync respects a configurable Jira project filter (optional — sync all assigned issues or limit to specific projects),Errors (auth failure, network, invalid config) produce clear actionable messages

- [ ] #2 Running 'taskbridge sync jira' fetches all open Jira issues assigned to the configured user,Each fetched Jira issue is created as a Todoist task (with title and Jira URL in description) if it does not already exist,Re-running the command does not create duplicate Todoist tasks for already-synced issues,Jira connection config (base URL, user email, API token) is stored via 'taskbridge config jira' with the same UX as other config commands,Sync respects a configurable Jira project filter (optional — sync all assigned issues or limit to specific projects),Errors (auth failure, network, invalid config) produce clear actionable messages
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create src/taskbridge/jira_api.py with JiraIssue dataclass and JiraAPI client\n2. Add Jira config methods to config.py (get/set base_url, email, api_token, project_filter)\n3. Add jira_todoist_sync table and CRUD methods to database.py\n4. Add 'config jira' and 'sync jira' commands to main.py\n5. Write unit tests in tests/unit/test_jira_api.py\n6. Run ruff + ty + pytest to verify
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Created src/taskbridge/jira_api.py with JiraAPI client and JiraIssue dataclass using Jira Cloud REST API v3 Basic Auth.\n\nAdded Jira config methods (get/set base_url, email, api_token, project_filter, validate_credentials) to config.py.\n\nAdded jira_todoist_sync table and JiraSyncRecord dataclass + CRUD methods (get_jira_sync, create_jira_sync, get_all_jira_syncs) to database.py.\n\nAdded 'taskbridge config jira' interactive wizard and 'taskbridge sync jira' command (with --dry-run, --project, --todoist-project flags) to main.py.\n\nWrote 10 unit tests in tests/unit/test_jira_api.py covering init, credential validation, issue mapping, pagination, project key filtering, and error propagation.\n\nAll 131 tests pass, ruff and ty clean.
<!-- SECTION:NOTES:END -->
