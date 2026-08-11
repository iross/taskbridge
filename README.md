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

## Development

```bash
just test        # unit tests
just test-all     # unit + integration tests
just lint         # ruff check
just format       # ruff format
just typecheck    # ty check
```

See `CLAUDE.md` for the Backlog.md task workflow and `backlog/decisions/` for architecture decisions.
