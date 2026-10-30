"""Tests for archiving backlog tasks into their parent Todoist task's note (ADR-004)."""

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from taskbridge import backlog, backlog_archive, frontmatter, task_notes
from taskbridge.config import Config
from taskbridge.database import Database, TodoistNoteMapping
from taskbridge.main import app
from taskbridge.todoist_api import TodoistTask

PARENT_URL = backlog.todoist_task_url("PARENT1")

MODERN = f"""---
id: TASK-32
title: Add project picker
status: Done
created_date: '2026-07-07 16:39'
updated_date: '2026-10-30 14:29'
labels:
  - web-ui
dependencies: []
references:
  - 'https://github.com/iross/taskbridge/pull/9'
  - '{PARENT_URL}'
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Pick projects.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Picker works
- [ ] #2 Free text works
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
### Approach
Datalist.
```python
## not a heading
# nor this
```
<!-- SECTION:NOTES:END -->
"""

LEGACY = """---
id: task-01
title: Set up package
status: Done
created_date: 2025-07-30
labels: []
dependencies: []
---

## Description

Create the package.

## Acceptance Criteria

- [x] Installs with uv

## Implementation Plan
"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A repo, vault, config and database wired into the archive code."""
    repo = tmp_path / "myrepo"
    vault = tmp_path / "vault"
    (vault / "10 Projects").mkdir(parents=True)
    cfg = Config(tmp_path / "cfg")
    cfg.set("obsidian_vault_path", str(vault))
    cfg.set("todoist_token", "token")
    database = Database(str(tmp_path / "test.db"))
    for module in (backlog_archive, task_notes):
        monkeypatch.setattr(module, "config_manager", cfg)
        monkeypatch.setattr(module, "db", database)
    monkeypatch.setattr("taskbridge.main.config_manager", cfg)
    monkeypatch.setattr(task_notes, "resolve_project_info", lambda pid, api: ("Picker", "CHTC"))

    api = MagicMock()
    parent = TodoistTask(id="PARENT1", content="Web UI polish", description="", project_id="p1")
    api.get_task.side_effect = lambda tid: parent if tid == "PARENT1" else None
    monkeypatch.setattr("taskbridge.main.TodoistAPI", lambda: api)
    return repo, vault, database, api


def mapping(note_path):
    return TodoistNoteMapping(
        todoist_task_id="PARENT1",
        todoist_project_id="p1",
        note_path=str(note_path),
        obsidian_url="obsidian://x",
    )


def write(repo, name, text, sub="tasks"):
    path = repo / "backlog" / sub / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def archive(repo, *args):
    return CliRunner().invoke(app, ["backlog", "archive", *args, "--repo", str(repo)])


class TestParseTask:
    def test_modern_file(self, tmp_path):
        task = backlog_archive.parse_task(write(tmp_path, "task-32 - X.md", MODERN))

        assert (task.id, task.title, task.status) == ("TASK-32", "Add project picker", "Done")
        assert (task.created, task.updated, task.labels) == ("2026-07-07", "2026-10-30", ["web-ui"])
        assert dict(task.sections) == {
            "Description": "Pick projects.",
            "Acceptance Criteria": "- [x] Picker works\n- [ ] Free text works",
            "Implementation Notes": (
                "#### Approach\nDatalist.\n```python\n## not a heading\n# nor this\n```"
            ),
        }

    def test_legacy_file_without_markers_drops_empty_sections(self, tmp_path):
        task = backlog_archive.parse_task(write(tmp_path, "task-01 - X.md", LEGACY, "completed"))

        assert task.id == "TASK-01"
        assert task.created == "2025-07-30"
        assert [heading for heading, _ in task.sections] == ["Description", "Acceptance Criteria"]


class TestParentId:
    def task(self, refs):
        return backlog_archive.BacklogTask("TASK-1", "t", "Done", "", "", [], refs, [])

    def test_ignores_non_todoist_references(self):
        assert backlog_archive.parent_id(self.task(["docs/x.md", PARENT_URL])) == "PARENT1"

    def test_same_task_twice_is_one_parent(self):
        slug = "https://app.todoist.com/app/task/web-ui-PARENT1"
        assert backlog_archive.parent_id(self.task([PARENT_URL, slug])) == "PARENT1"

    def test_unlinked(self):
        assert backlog_archive.parent_id(self.task([])) is None

    def test_two_parents_is_an_error(self):
        other = backlog.todoist_task_url("OTHER")
        with pytest.raises(backlog_archive.ArchiveError, match="2 Todoist tasks"):
            backlog_archive.parent_id(self.task([PARENT_URL, other]))


class TestArchiveCommand:
    def test_creates_parent_note_and_appends_section(self, env):
        repo, vault, database, api = env
        write(repo, "task-32 - X.md", MODERN)

        result = archive(repo, "32")

        assert result.exit_code == 0, result.output
        note = vault / "10 Projects" / "Picker" / "Web UI polish.md"
        assert "TASK-32 → 10 Projects/Picker/Web UI polish.md (added)" in result.output
        lines, body = frontmatter.split(note.read_text())
        meta = frontmatter.load(lines)
        assert meta["backlog_tasks"] == ["myrepo/TASK-32"]
        assert meta["tags"] == ["backlog", "backlog/myrepo"]
        assert meta["client"] == "CHTC"
        assert "## myrepo TASK-32 — Add project picker" in body
        assert "Done · created 2026-07-07 · updated 2026-10-30 · labels: web-ui" in body
        assert "<!-- SECTION" not in body and "#1" not in body
        assert database.get_todoist_note_by_task_id("PARENT1").note_path == str(note)

    def test_many_tasks_share_one_parent_note_and_keep_existing_content(self, env):
        repo, vault, database, _ = env
        note = vault / "10 Projects" / "Picker" / "Web UI polish.md"
        note.parent.mkdir(parents=True)
        note.write_text(
            "---\nfileClass: task\ntags: ['web']\n---\n\n# Web UI polish\n\nMy notes.\n"
        )
        database.create_todoist_note_mapping(mapping(str(note)))
        write(repo, "task-32 - X.md", MODERN)
        write(repo, "task-33 - Y.md", MODERN.replace("TASK-32", "TASK-33"))

        assert archive(repo, "32", "33").exit_code == 0

        text = note.read_text()
        assert text.startswith("---\nfileClass: task\n")
        assert "# Web UI polish\n\nMy notes.\n\n<!-- backlog:myrepo/TASK-32 -->" in text
        assert text.index("TASK-32 —") < text.index("TASK-33 —")
        meta = frontmatter.load(frontmatter.split(text)[0])
        assert meta["backlog_tasks"] == ["myrepo/TASK-32", "myrepo/TASK-33"]
        assert meta["tags"] == ["web", "backlog", "backlog/myrepo"]

    def test_rerun_skips_and_force_replaces_only_that_section(self, env):
        repo, vault, _, _ = env
        path = write(repo, "task-32 - X.md", MODERN)
        write(repo, "task-33 - Y.md", MODERN.replace("TASK-32", "TASK-33"))
        archive(repo, "32", "33")
        note = vault / "10 Projects" / "Picker" / "Web UI polish.md"
        first = note.read_text()

        rerun = archive(repo, "32")
        assert "TASK-32 already in" in rerun.output
        assert note.read_text() == first

        path.write_text(MODERN.replace("Pick projects.", "Pick projects, revised."))
        forced = archive(repo, "32", "--force")

        assert "(replaced)" in forced.output
        text = note.read_text()
        assert "Pick projects, revised." in text
        assert text.count("<!-- backlog:myrepo/TASK-32 -->") == 1
        assert text.count("<!-- backlog:myrepo/TASK-33 -->") == 1
        assert text.index("TASK-32 —") < text.index("TASK-33 —")
        assert frontmatter.load(frontmatter.split(text)[0])["backlog_tasks"] == [
            "myrepo/TASK-32",
            "myrepo/TASK-33",
        ]

    def test_force_with_unchanged_task_leaves_note_identical(self, env):
        repo, vault, _, _ = env
        write(repo, "task-32 - X.md", MODERN)
        write(repo, "task-33 - Y.md", MODERN.replace("TASK-32", "TASK-33"))
        archive(repo, "32", "33")
        note = vault / "10 Projects" / "Picker" / "Web UI polish.md"
        first = note.read_text()

        archive(repo, "32", "33", "--force")

        assert note.read_text() == first

    def test_done_selects_done_tasks_and_reports_unlinked(self, env):
        repo, vault, _, _ = env
        write(repo, "task-32 - X.md", MODERN)
        write(repo, "task-34 - Z.md", MODERN.replace("status: Done", "status: To Do"))
        write(repo, "task-01 - Old.md", LEGACY, "completed")

        result = archive(repo, "--done")

        assert result.exit_code == 0, result.output
        assert "TASK-32 →" in result.output
        assert "TASK-34" not in result.output
        assert "Not linked to a Todoist task, skipped: TASK-01" in result.output

    def test_done_runs_in_task_number_order(self, env):
        repo, _, _, _ = env
        unlinked = MODERN.replace(f"  - '{PARENT_URL}'\n", "")
        for name, sub in [
            ("task-10 - A.md", "tasks"),
            ("task-9 - B.md", "completed"),
            ("task-9.2 - C.md", "tasks"),
        ]:
            write(repo, name, unlinked, sub)

        result = archive(repo, "--done")

        assert "skipped: TASK-9, TASK-9.2, TASK-10" in result.output

    def test_missing_parent_is_reported_and_others_continue(self, env):
        repo, vault, _, _ = env
        missing = backlog.todoist_task_url("GONE")
        write(repo, "task-35 - G.md", MODERN.replace(PARENT_URL, missing))
        write(repo, "task-32 - X.md", MODERN)

        result = archive(repo, "35", "32")

        assert result.exit_code == 1
        assert "TASK-35: parent Todoist task GONE not found" in result.output
        assert "TASK-32 →" in result.output

    def test_note_moved_to_archive_is_found(self, env):
        repo, vault, database, _ = env
        mapped = vault / "10 Projects" / "Picker" / "Web UI polish.md"
        archived = vault / "40 Archive" / "Picker" / "Web UI polish.md"
        archived.parent.mkdir(parents=True)
        archived.write_text("---\nfileClass: task\n---\n")
        database.create_todoist_note_mapping(mapping(str(mapped)))
        write(repo, "task-32 - X.md", MODERN)

        result = archive(repo, "32")

        assert "→ 40 Archive/Picker/Web UI polish.md (added)" in result.output
        assert "TASK-32 —" in archived.read_text()

    def test_mapped_note_gone_everywhere_is_an_error(self, env):
        repo, vault, database, _ = env
        database.create_todoist_note_mapping(mapping(str(vault / "elsewhere.md")))
        write(repo, "task-32 - X.md", MODERN)

        result = archive(repo, "32")

        assert result.exit_code == 1
        assert "note is missing" in result.output

    def test_start_marker_without_end_is_an_error_and_note_untouched(self, env):
        repo, vault, database, _ = env
        note = vault / "n.md"
        note.write_text("---\na: 1\n---\n<!-- backlog:myrepo/TASK-32 -->\nhand edited\n")
        database.create_todoist_note_mapping(mapping(str(note)))
        write(repo, "task-32 - X.md", MODERN)
        before = note.read_text()

        result = archive(repo, "32", "--force")

        assert result.exit_code == 1
        assert "not its end marker" in result.output
        assert note.read_text() == before

    def test_dry_run_writes_nothing(self, env):
        repo, vault, database, api = env
        path = write(repo, "task-32 - X.md", MODERN)
        repo_before = path.read_text()

        result = archive(repo, "32", "--dry-run")

        assert result.exit_code == 0, result.output
        assert "→ 10 Projects/Picker/Web UI polish.md (would create note and add)" in result.output
        assert not (vault / "10 Projects" / "Picker").exists()
        assert database.get_todoist_note_by_task_id("PARENT1") is None
        api.create_comment.assert_not_called()
        assert path.read_text() == repo_before

    def test_dry_run_reports_existing_sections(self, env):
        repo, _, _, _ = env
        write(repo, "task-32 - X.md", MODERN)
        archive(repo, "32")

        assert "already in" in archive(repo, "32", "--dry-run").output
        assert "(would replace)" in archive(repo, "32", "--dry-run", "--force").output

    def test_repo_files_never_modified(self, env):
        repo, _, _, _ = env
        path = write(repo, "task-32 - X.md", MODERN)

        archive(repo, "32")
        archive(repo, "32", "--force")

        assert path.read_text() == MODERN

    @pytest.mark.parametrize("args", [[], ["32", "--done"]])
    def test_needs_ids_or_done_but_not_both(self, env, args):
        repo, _, _, _ = env

        result = archive(repo, *args)

        assert result.exit_code == 1
        assert "Name the tasks to archive or pass --done" in result.output
