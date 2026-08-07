---
id: TASK-38
title: Add Apple Mail inbox adapter
status: To Do
assignee: []
created_date: '2026-08-07 18:53'
labels: []
dependencies:
  - TASK-36
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Detect unprocessed mail (unread or still in Inbox), actioned mail (replied, or moved to a project mailbox), and filed mail (archived with no reply) via AppleScript/JXA, and wire it into 'inbox report'. Registered under module name 'mail' so it can be disabled entirely for profiles like home that shouldn't see a work inbox.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Adapter correctly classifies a message into unprocessed/actioned/filed based on read state, reply state, and mailbox location,Adapter is isolated behind a function boundary so it can be tested with a fake AppleScript response,Adapter is not invoked at all when the 'mail' module is disabled for the active profile,Failure to reach Mail.app (not running, permissions denied) produces a clear error, not a silent zero count,'inbox report' includes Mail counts and oldest-unprocessed age when enabled,Each returned message includes a message://<message-id> URI captured via AppleScript so it can be opened directly in Mail for reply
<!-- AC:END -->
