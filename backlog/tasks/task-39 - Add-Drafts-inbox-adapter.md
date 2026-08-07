---
id: TASK-39
title: Add Drafts inbox adapter
status: To Do
assignee: []
created_date: '2026-08-07 18:53'
labels: []
dependencies:
  - TASK-36
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Detect drafts still sitting in the Inbox workspace vs. actioned (sent to another app) vs. filed (archived), and wire it into 'inbox report'. Registered under module name 'drafts' for profile toggling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Adapter distinguishes Inbox-workspace drafts from archived/actioned drafts,Adapter is not invoked when the 'drafts' module is disabled for the active profile,Adapter is isolated behind a function boundary so it can be tested without Drafts running,'inbox report' includes Drafts counts and oldest-unprocessed age when enabled,Each returned draft includes a drafts://open?uuid=<uuid> URI so it can be opened directly in Drafts
<!-- AC:END -->
