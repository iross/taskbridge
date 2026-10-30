# TaskBridge

Python/Typer CLI integrating Todoist, Obsidian, Google Calendar, Jira, and bartib time tracking.

## Install

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[test,dev]"
```

Commands can also be run without activating, via `uv run taskbridge ...`.

## Configure

```bash
taskbridge config todoist    # sets todoist_token
taskbridge config obsidian   # sets obsidian_vault_path / obsidian_vault_name
taskbridge config jira       # sets jira_base_url / jira_email / jira_api_token
taskbridge config gcal       # sets up Google Calendar OAuth2 credentials
```

Config is stored at `~/.taskbridge/config.yaml`.

## Unified inbox report (ADR-002 / ADR-003)

Reports outstanding items across Obsidian folders and the Todoist Inbox project from one command,
gated by a per-machine profile so work-only sources (e.g. Mail, once built) stay off at home.

There's no CLI command yet for the config keys below — add them to `~/.taskbridge/config.yaml` by
hand:

```yaml
inbox_folders:
  - label: inbox
    path: "00 Inbox" # relative to obsidian_vault_path
  - label: literature
    path: "30 Resources/37 Literature"
default_profile: home
profiles:
  home:
    enabled_modules: [obsidian_inbox, todoist_inbox]
  work:
    enabled_modules: [obsidian_inbox, todoist_inbox, mail, drafts]
```

Usage:

```bash
taskbridge inbox report                 # uses default_profile
taskbridge inbox report --profile work  # preview another profile without editing config
taskbridge inbox open <index>           # launch the item's native URI (obsidian://, todoist showTask link, ...)
```

`inbox open` shells out to the macOS `open` command, so it only works on a Mac.

## Linking backlog tasks to Todoist tasks (ADR-004)

A [backlog.md](https://github.com/MrLesk/Backlog.md) task can name the Todoist task it is part of.
The link is the Todoist task URL in the backlog task's `references`, so it survives `backlog task
edit` and many backlog tasks can share one parent.

```bash
taskbridge backlog link                          # pick backlog tasks (TAB for several), then the parent
taskbridge backlog link TASK-49 50               # name the tasks, pick the parent
taskbridge backlog link 49 50 --to 6gRPQ6W25287Ccx7  # or give the parent's ID or pasted URL
taskbridge backlog link 49 --repo ~/projects/other
```

The backlog picker lists the repo's tasks newest first with status and a 🔗 on ones already
linked, and previews each task. The parent picker shows which backlog tasks you are linking and
lists the Todoist task you are currently time-tracking first.

Linking replaces any earlier Todoist link and keeps other references. It also works on tasks in
`backlog/completed/`, which the backlog CLI itself cannot edit.

Archiving appends linked tasks to the parent Todoist task's Obsidian note (creating the note if
needed), so the note collects the design and implementation notes of everything done for it:

```bash
taskbridge backlog archive --done --dry-run   # show where each Done task would go
taskbridge backlog archive --done             # append every Done task
taskbridge backlog archive TASK-45 TASK-46    # or name tasks
taskbridge backlog archive TASK-45 --force    # replace a section archived earlier
```

Each task becomes a `## <repo> <TASK-ID> — <title>` section between `<!-- backlog:<repo>/<ID> -->`
marker comments; re-runs skip it unless `--force`. The note's frontmatter gets `backlog_tasks`
(`<repo>/<ID>` entries) and the tags `backlog` and `backlog/<repo>`. Unlinked tasks are skipped
and listed. Repo files are never changed. A note whose project was moved to `40 Archive/` is
still found there.

Each section also gets a **Provenance** list of the commits whose messages mention the task ID
(`task-9`, `TASK-09`, `(task-9)` all count; `task-90` and `task-9.1` don't), oldest first, plus
any GitHub pull requests containing them. Merges and commits that only touch `backlog/` are left
out. Commits link to GitHub once pushed; PRs need the `gh` CLI. Put the task ID in commit
messages (e.g. `Add archive command (task-45)`) for this to find them.

## Development

```bash
just test        # unit tests
just test-all     # unit + integration tests
just lint         # ruff check
just format       # ruff format
just typecheck    # ty check
```

See `CLAUDE.md` for the Backlog.md task workflow and `backlog/decisions/` for architecture decisions.
