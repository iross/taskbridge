---
id: TASK-46
title: Add git and PR provenance to archived backlog task notes
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-16 17:56'
updated_date: '2026-10-30 15:29'
labels:
  - obsidian
  - backlog
  - git
dependencies:
  - TASK-45
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
An archived backlog task is more useful as a record when it shows where the work actually happened: the commits that implemented it and the PR that merged it. Since TASK-45 appends archived tasks to the parent Todoist task's note, this history belongs inside each task's appended section.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Commits link to GitHub when the repo origin is GitHub; otherwise they show the short SHA
- [x] #2 Associated PRs are listed with title and URL (via gh) when available
- [x] #3 A missing gh, non-GitHub remote, or API failure prints a warning and the note is still archived without PR links
- [x] #4 Each task section appended by backlog archive gets a Provenance subsection listing commits whose messages mention the task ID; matching is case-insensitive and zero-padding aware (task-09 = TASK-9) and task-4 does not match task-43
- [x] #5 Tasks with no matching commits get no Provenance subsection
- [x] #6 Commits that change only files under backlog/ (task bookkeeping) are not listed
- [x] #7 Commits not yet on any remote show the short SHA without a link
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. provenance.py: read the repo history once per run (git log --no-merges with messages and changed files), GitHub owner/repo from origin, set of pushed commits
2. Match task IDs in messages: case-insensitive, zero-padding aware, not a prefix of a longer ID; drop backlog-only commits
3. PR lookup per matching commit via gh api repos/<o>/<r>/commits/<sha>/pulls, cached; missing gh / non-GitHub / API failure -> one warning, PR lookups stop, archive continues
4. Render a Provenance subsection (commits oldest first, then PRs) inside each archived section; none when no commits match
5. backlog archive builds the history once and prints warnings after the per-task lines
6. Tests: real temp git repos for history/matching; gh mocked at the subprocess boundary
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- New src/taskbridge/provenance.py: RepoHistory reads the repo once per archive run (git log --no-merges with messages and changed files, origin's GitHub owner/repo, commits reachable from remote-tracking refs) and renders a Provenance subsection per task; backlog archive adds it inside each section and prints its warnings once after the per-task lines. --dry-run reads no history.
- Matching: task_id_pattern is case-insensitive, ignores zero padding, handles subtask IDs, and will not match a longer ID (task-90, task-9.1) or a prefixed word (subtask-9).
- Added AC #6/#7: bookkeeping commits (changed files all under backlog/) are dropped, and unpushed commits show a short SHA instead of a link that would 404. Empty commits that mention the task are kept.
- PRs: gh api repos/<o>/<r>/commits/<sha>/pulls for pushed commits only, cached and de-duplicated. Missing gh, a non-GitHub origin, or a failed lookup each give one warning; after a failure no further lookups are attempted. Not a git repo: warning, no Provenance.
- Bug found against real history: git quotes non-ASCII paths, so bookkeeping commits on emoji-named task files looked like code commits. Fixed with core.quotePath=false.
- Only ~20 of 134 commits here mention a task ID; provenance depends on the (task-NN) subject convention, now documented in the README.
- Tests: tests/unit/test_provenance.py (real temp git repos, gh faked at the subprocess boundary), archive integration tests in test_backlog_archive.py; all mutation checks caught.
<!-- SECTION:NOTES:END -->
