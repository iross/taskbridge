# ADR-002: Unified Location-Based Inbox Model for Cross-Tool Triage

## Status

**Proposed** - 2026-08-07

## Context

Work and notes enter through several unconnected capture surfaces: Apple Mail,
Drafts, an Obsidian "00 Inbox" folder for loose notes, a Readwise-synced
"30 Resources/37 Literature" folder for highlights, and a Todoist Inbox
project for uncategorized tasks. Each has to be checked separately to know
whether anything needs attention, and there's no single view of "what's
still unprocessed across everything."

taskbridge already integrates Todoist, Jira, Google Calendar, and bartib
as independent modules (`todoist_api.py`, `jira_api.py`, `gcal_integration.py`,
`bartib_integration.py`) wired into `main.py` via command groups. This
decision extends that pattern rather than building a separate tool, since
a prior placeholder (task-20, "Make it a TUI") already anticipated a
taskbridge-native interface layer and is superseded by this work.

## Decision

Track each source's state as **Inbox → {Actioned, Filed}**. Actioned means
a task was created or a reply was sent; Filed means the item was reviewed
and archived with no action needed. Both count as "processed" for
inbox-zero purposes; the split exists only for reporting (how much triage
time produced real work vs. filing).

State is **inferred from each tool's native signal**, never duplicated in
taskbridge's own database — avoiding drift between what taskbridge believes
and what the tool of record shows.

| Source | Unprocessed signal | Actioned signal | Filed signal |
|---|---|---|---|
| Obsidian `00 Inbox/` | in folder | — | moved out |
| Obsidian `30 Resources/37 Literature/` | in folder | — | moved out |
| Todoist Inbox project | task in project | moved to real project | n/a |
| Apple Mail | unread / in Inbox | replied, or moved to project mailbox | archived, no reply |
| Drafts | in Inbox workspace | sent to another app | archived |

The two Obsidian folders and the Todoist Inbox project share one mechanism
— a generic **folder/location-residency scanner** — rather than bespoke
code per source. Mail and Drafts need real adapters (AppleScript/JXA and
Drafts' URL scheme/CLI, respectively) since their state isn't file-location-based.

v1 is **read-only**: a new `inbox` command group reports counts and
oldest-item age per source. No in-tool actions, no AI-assisted triage.

## Implementation

- `taskbridge inbox report` — runs all configured scanners, prints a
  checklist with count + oldest age per bucket
- Obsidian/Todoist scanners are pure functions callable from tests without
  hitting the filesystem/network directly (mockable boundaries)
- Mail/Drafts adapters are Mac-only and must be built and tested on the
  actual machine — this can't be validated on a Linux dev box
- A Textual TUI is a later, separate layer wrapping the same report
  functions interactively; the CLI report must work standalone first

## Consequences

### Positive
- No dual-bookkeeping — taskbridge never disagrees with the tool of record
  about an item's state
- Matches the existing per-service module pattern; low architectural risk
- v1 ships value (a single "what's outstanding" checklist) before any
  Mac-native adapter exists, since Obsidian + Todoist scanners need nothing
  platform-specific

### Negative
- Mail and Drafts adapters require real testing on macOS; can't be
  developed and verified in a portable/CI environment
- Location-based detection is coarser than tagging — moving a note early
  or leaving it in a folder on purpose both look identical to "unprocessed"

### Neutral
- Fantastical integration is explicitly deferred pending investigation of
  its own API vs. reusing `gcal_integration.py`
- Folder-based Obsidian tracking may later be supplemented with a tagging
  system, per user preference to start simple

## Future Considerations

1. Fantastical adapter (own API vs. Google Calendar reuse)
2. In-TUI actions (archive/mark-done from the tool itself)
3. pydantic-ai-assisted triage (summarize threads, suggest whether a note
   needs a task) — layered on top of, not replacing, the deterministic report
4. Tag-based Obsidian state as an alternative/supplement to folder location
5. task-20 (Make it a TUI) archived as superseded by this ADR

## References

- Task-20: Make it a TUI (superseded, archived)
- Implementation breakdown for this decision: see backlog tasks created alongside it
- ADR-001: Adopt Zeit for Local-First Time Tracking (prior art for module pattern)
