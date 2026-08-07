---
id: DRAFT-01
title: Write-capable actions beyond the read-only inbox report
status: Draft
assignee: []
created_date: '2026-08-07 18:54'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
ADR-002 scoped v1 of the inbox model as strictly read-only (report what's outstanding, don't act on it). Several ideas already exist for actions that mutate state instead of just reporting it. None are scoped enough to be real tasks yet; this is a holding pen until one is picked up and fleshed out.

Known candidates so far:
1. Link a Mail message into a task's Obsidian note ('this email is relevant to this task') - grab the message's message:// URI + subject via AppleScript (likely the currently-selected message, no search needed) and append it under a References section on the target note. Open questions: how the target note is chosen (task ID lookup via the existing todoist_notes mapping, an interactive picker, or the currently-open Obsidian note), one-way vs. bidirectional linking, and what happens when the task has no note yet.
2. In-TUI actions (archive/mark-done/move directly from the tool, rather than only viewing counts) - ADR-002 future consideration #2.
3. pydantic-ai-assisted triage (summarize a thread, draft a reply, suggest whether a note needs a task) - ADR-002 future consideration #3. Action-adjacent even if it only drafts text, since it's producing something meant to be sent/used rather than just reporting state.

Promote to a real task once one of these has clear enough scope to write acceptance criteria against.
<!-- SECTION:DESCRIPTION:END -->
