---
id: TASK-33
title: Render tags as colored pills in CLI and web UI
status: Done
assignee:
  - '@claude'
created_date: '2026-07-08 15:00'
updated_date: '2026-07-08 16:04'
labels:
  - web-ui
  - cli
  - time-tracking
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Tags now surface in the timeline, current card, and report label sections as plain chips/text. Colored pills make tags scannable at a glance. Colors should be assigned automatically per tag so untouched tags always look consistent, with user-configurable overrides for tags where a specific color matters.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Web UI tag chips render as pills with a per-tag color derived automatically from the tag name
- [x] #2 CLI output that lists tags (report labels, meeting list) renders tags as colored pills
- [x] #3 A tag's color can be overridden via configuration and both CLI and web UI honor the override
- [x] #4 Auto-assigned colors are stable across runs and readable in both light and dark web UI themes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Colors: TAG_PALETTE (the 10 client colors) with a stable hash (h*31 & 0xffff) shared between Python tag_color() and JS tagColor(), so a tag gets the same color in CLI and web UI. Overrides stored in config as tag_colors {tag: '#rrggbb', keys lowercase}, managed via 'taskbridge config tag-color [tag] [color] [--remove]' (validates #rrggbb) and served to the browser in the /api/status payload.

CLI: format_tag_pill() renders ' tag ' with a truecolor background via typer.style (no new dependency — typer re-exports click styling); text is black or white by background luminance; ANSI is stripped automatically on non-TTY output so piped/emailed reports stay plain. Pills used in report Labels section, meeting list, and task Labels lines.

Web UI: chips are colored with color-mix tints (16% background, 50% border, text mixed 60% toward var(--text)) so pills stay readable in both themes; invalid override values are ignored client-side (regex check) and rejected at set time by the CLI. Applied in timeline chips, current card, and daily report Labels rows.

Also removed two redundant function-local 'import re' statements in main.py after adding the module-level import.

Files: src/taskbridge/main.py, src/taskbridge/config.py, src/taskbridge/web_ui.py, tests/unit/test_tag_colors.py (new), tests/unit/test_report.py, tests/unit/test_meetings.py. 194 tests pass; ruff and ty clean. Verified live: TTY report shows colored pills, override set/list/remove works end-to-end including the web payload, piped output has no ANSI.
<!-- SECTION:NOTES:END -->
