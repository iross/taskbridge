# Apple Reminders as a Todoist Substitute — Feature & Architecture Mapping

**Status**: Research, not a decision. Written 2026-08-07 to inform whether/how to move TaskBridge off Todoist.

## Why this matters for TaskBridge specifically

TaskBridge isn't just a task list viewer — `todoist_task_id` is a foreign key threaded through three
other subsystems in `database.py`:

- `todoist_notes` — Obsidian note ↔ task mapping
- `task_time_tracking` — bartib time entries linked to a task
- `jira_todoist_sync` — Jira issue ↔ task mapping

All of that, plus `sync projects`/`sync jira`/`sync notes`, `task list --filter`, and project
create/archive, is driven by Todoist's **hosted REST API** (`api.todoist.com/api/v1`) authenticated
with a bearer token (`config_manager.get_todoist_token()`). That's what makes today's design work
headlessly from any machine (Linux, CI, whatever) with just a token in config — no Apple hardware
required.

That last point is the crux of this doc: **Apple Reminders has no equivalent hosted API.** Everything
below has to be read through that lens.

## The access-method landscape (2026)

Apple has never shipped a cloud REST API for Reminders. Every integration path is one of these:

| Method | Where it runs | What it can touch | Stability |
|---|---|---|---|
| **EventKit** (public framework) | On-device, macOS/iOS only | Lists, reminders, due dates, priority (coarse), notes, recurrence, completion | Apple-supported, stable across OS versions |
| **AppleScript** | macOS only | Similar to EventKit plus a few UI-level things (e.g. flags) | Works, but Apple has been quietly deprioritizing AppleScript for years |
| **Private `ReminderKit`** (undocumented) | macOS only, needs Full Disk Access | Tags, subtasks, sections, smart lists, list groups, sharing metadata, flags, "urgent" state | Unsupported by Apple — can break on any OS update, no warranty |
| **CalDAV** (`caldav.icloud.com`) | Any OS, cross-platform | Title, notes, due date, priority (raw 1-9 field), completion — standard VTODO only | Stable protocol, but Apple's proprietary post-iOS-13 features (tags, subtasks, sections, smart lists) **don't exist in CalDAV at all** |
| **Shortcuts / App Intents** | On-device Apple only | Whatever Shortcuts actions expose (close to EventKit-level) | Supported, but still local-only, and shelling out to `shortcuts run` is a workaround, not an API |

There is no path that is both (a) cross-platform/headless and (b) full-fidelity. You trade one for
the other.

## Feature-by-feature mapping

| Todoist (today) | Reminders equivalent | Gap |
|---|---|---|
| Bearer-token REST API, callable from any OS/CI | None — nearest is CalDAV (cross-platform) or EventKit/ReminderKit (Mac-only) | **Structural.** TaskBridge would become Mac-only (EventKit/ReminderKit path) or feature-reduced (CalDAV path) |
| Projects: nested (`parent_id`), color, favorite, archive, create via API | Lists + List Groups | Groups give one level of nesting, not arbitrary depth. No "archive" concept — only delete, or manual move to a groups folder |
| Labels: colored, cross-project, `task labels` listing | Tags | Tags exist in the Reminders UI (since ~2021) but are **not exposed in public EventKit** — only reachable via private ReminderKit. CalDAV can't see them either |
| `--filter` query language (`task list -f "today | p1"`) → `/tasks/filter` | Smart Lists | Conceptually similar (a saved filter), but it's a GUI/private-API object, not an ad-hoc query string a CLI can pass. Community tooling (RemCTL) can create/edit smart lists but notes "not all filter families materialize reliably" |
| Priority: 4 discrete levels (1–4) | Priority: none/low/medium/high | EventKit buckets a 0/1–4/5–8/9 scale into roughly none/low/med/high — coarser, but a workable mapping |
| Due dates: natural-language `due_string`, `due_date`, `due_datetime`, recurrence | Due date/time + `EKRecurrenceRule` | Recurrence has solid public-API parity. Natural-language parsing is server-side in Todoist; on Reminders it's whatever the client (in-app or CLI tool) implements — less robust |
| Subtasks (`parent_id` on task) | Subtasks | Recently added to Reminders.app but only reliably read/write via private ReminderKit, not public EventKit |
| Sections within a project | Sections within a list | Same private-API-only caveat as subtasks |
| Comments on a task (`create_comment`, threaded) | Single `notes` field | Reminders has no comment thread — one description field, full stop |
| `move_task` between projects (Sync API) | Move reminder between lists | Supported at the EventKit level, fine |
| Task URL (`todoist.com/task/...`) | No public URL scheme | Private/undocumented deep links only (`x-apple-reminderkit://...`), unstable |
| Shared projects, `assignee_id`/`assigner_id` | Shared lists, assign to member | Conceptually comparable, but far less visible/queryable programmatically |

## Tooling that exists today

- **[reminders-cli](https://github.com/keith/reminders-cli)** (Keith Smiley) — thin, public-EventKit-only Swift CLI. `show-lists`, `show`, `add`, `complete`, `edit`, `delete`, due dates, priority. No tags, no subtasks, no JSON output as far as the docs show. Stable because it only uses public API.
- **[RemCTL](https://github.com/viticci/remctl)** (Federico Viticci) — by far the most complete: sections, subtasks, tags, smart lists, sharing, flags, groceries lists, templates, JSON output explicitly designed for AI-agent/automation use. Gets this by reading the local iCloud Reminders database directly and writing through a mix of public EventKit and private ReminderKit. Requires macOS 26+, Full Disk Access, and an explicit `--private` flag for the unsupported parts. Its own docs flag partial-write races and smart-list fidelity issues.
- **remindctl**, **rem**, **apple-reminders-cli** — smaller/newer entrants, roughly EventKit-level feature sets.
- **MCP servers** (`mcp-server-apple-events`, `apple-productivity-mcp`) — wrap EventKit/AppleScript for LLM agent use; same underlying limitations apply.

None of these are a hosted service you point a bearer token at — they're all local processes that need to run somewhere Reminders' database actually lives.

## What full migration would mean for TaskBridge concretely

- `todoist_api.py` gets replaced by a local EventKit/ReminderKit bridge (Swift helper binary, or shelling out to RemCTL/reminders-cli) — not a drop-in HTTP client swap.
- **TaskBridge becomes Mac-only** for anything touching tasks, since Obsidian-note-mapping, time tracking, and Jira sync all key off task IDs that only exist reachably on-device. Today those same commands work from Linux/CI with just a token.
- Labels, filter queries, and subtasks — all actively used (`task labels`, `--filter`, `--label`) — would need the private ReminderKit path, which is explicitly unsupported by Apple and has already broken across OS updates for other tools.
- "Archive project" (used in `project archive`) has no clean equivalent — only delete.
- Task URLs stored/displayed today (`task.url`) would lose their stable, shareable link.

## Recommendation

Given how much of TaskBridge's value (Jira sync, Obsidian mapping, time tracking) depends on a
stable, headless, cross-platform API, a **full swap looks like a downgrade, not a lateral move** —
you'd trade a supported hosted API for either a feature-reduced protocol (CalDAV) or an
unsupported/local-only private API (ReminderKit).

If the goal is genuinely to stop paying for/using Todoist, two narrower options are more realistic
than a full swap:

1. **Partial migration** — keep Todoist (or move to CalDAV-backed Reminders) for personal, low-stakes
   quick-capture reminders that don't need labels/subtasks/filters, and keep the Jira/Obsidian/time-tracking-linked
   workflow on Todoist (or another hosted service with a real API) since that's where the sync
   guarantees actually matter.
2. **Pilot on a single Mac** using RemCTL before committing — it's the only tool with near-full
   feature parity, but test its private-API paths against your actual daily workflow (labels, filters,
   subtasks) before trusting it, since Apple could break that path in any future OS update.

Sources:
- [reminders-cli](https://github.com/keith/reminders-cli)
- [RemCTL](https://github.com/viticci/remctl)
- [Apple Support: Access iCloud Mail, Calendar, and Contacts in third-party apps](https://support.apple.com/en-us/121539)
- [Apple Support: app-specific passwords](https://support.apple.com/en-us/102654)
- [DAVx⁵ — tested with iCloud](https://www.davx5.com/tested-with/icloud)
- [Tasks.org — iCloud CalDAV synchronization](https://tasks.org/docs/caldav_icloud/)
- [EventKit — Apple Developer Documentation](https://developer.apple.com/documentation/eventkitui)
