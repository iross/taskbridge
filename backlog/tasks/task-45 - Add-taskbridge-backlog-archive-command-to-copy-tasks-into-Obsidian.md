---
id: TASK-45
title: Add taskbridge backlog archive command to copy tasks into Obsidian
status: To Do
assignee: []
created_date: '2026-10-16 17:56'
labels:
  - obsidian
  - backlog
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Finished backlog.md tasks hold design rationale and implementation notes that should live with the project in the Obsidian vault, in the vault's own note format, instead of staying only in each repo. Copying (not moving) keeps the repo's task history intact and avoids backlog.md reusing IDs of deleted tasks. Notes go inside the project folder so they follow the project into 40 Archive when the project is archived.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 taskbridge backlog archive [IDS...] [--done] [--repo PATH] [--dry-run] copies the chosen tasks from the repo (default: cwd) into <vault>/10 Projects/<Project>/backlog/; --done selects every task with status Done (in tasks/ or completed/)
- [ ] #2 Each note has vault-style frontmatter (fileClass: task, project, client, status, created, completed, tags: [backlog, backlog/<repo>, ...labels]) and keeps backlog metadata as backlog_id, backlog_repo, backlog_source, backlog_dependencies
- [ ] #3 Note body keeps description, acceptance criteria (as checkboxes), plan and implementation notes as headings, with no backlog SECTION/AC marker comments
- [ ] #4 Filenames include the repo (e.g. 'taskbridge TASK-43 - <title>.md') so two repos mapped to one project never collide
- [ ] #5 Repo -> (project, client) mapping is stored in taskbridge config; when missing the command prompts with existing 10 Projects folders and defaults client to the one most used by that folder's notes; --project/--client set it without prompting
- [ ] #6 A task already archived (note with same backlog_repo + backlog_id exists) is skipped and reported; --force overwrites it
- [ ] #7 Repo files are never modified; --dry-run prints planned destinations and writes nothing
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation pointers:
- Parse task files directly (YAML frontmatter + SECTION markers); yaml is already a dependency.
- Reuse config.get_obsidian_vault_path() and get_obsidian_projects() in src/taskbridge/config.py.
- New module src/taskbridge/backlog_archive.py; backlog_app typer group in main.py.
- Status map: Done->done, In Progress->in_progress, To Do->todo (vault project fileClass values).
Out of scope for v1: sweeping all repos under ~/projects, an inbox source for done-but-unarchived tasks, moving/deleting tasks from repos.
<!-- SECTION:NOTES:END -->
