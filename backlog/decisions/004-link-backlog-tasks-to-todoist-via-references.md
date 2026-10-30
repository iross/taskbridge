# ADR-004: Link Backlog Tasks to Todoist Tasks via `references`

## Status

**Accepted** - 2026-10-30

## Context

backlog.md tasks live in each repo and have no connection to taskbridge
tasks. A taskbridge task is a Todoist task: time tracking is keyed by
Todoist task ID, and Obsidian task notes are one-to-one with Todoist tasks
(`todoist_notes`). Synthetic tracking IDs (`meeting:`, `cal:`, `ongoing:`)
and project-only starts have no note and are not work items a backlog task
could belong to.

Several backlog tasks often implement one piece of work tracked as a single
Todoist task, and their design rationale should end up in that task's note.

A custom frontmatter key (e.g. `taskbridge_task:`) does not work: the
backlog CLI (1.47) rewrites the file on every `backlog task edit` and drops
keys it does not know.

## Decision

A backlog task names its parent taskbridge task with a Todoist task URL in
its built-in `references` list:

```yaml
references:
  - 'https://app.todoist.com/app/task/6gRPQ6W25287Ccx7'
```

- Many backlog tasks may reference the same Todoist task; a backlog task has
  at most one Todoist reference.
- taskbridge writes the canonical `https://app.todoist.com/app/task/<id>`
  form and also reads the browser form `.../task/<slug>-<id>` (Todoist IDs
  contain no hyphens).
- The repo file is the only place the link is stored; taskbridge keeps no
  mapping table for it.
- When a linked backlog task is archived, its content is appended to the
  parent Todoist task's Obsidian note rather than written as its own note.

## Consequences

- The link survives backlog CLI edits, shows in `backlog task <id> --plain`,
  and is clickable.
- The vault project and client come from the parent Todoist task, so no
  repo-to-project mapping is needed.
- Backlog tasks with no Todoist reference cannot be archived into a note;
  linking them first is a deliberate step.
- A parent completed or deleted in Todoist before its note exists cannot be
  resolved to a note.
