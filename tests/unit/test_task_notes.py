"""Tests for task_notes.get_or_create_task_note, shared by the web UI and backlog archive."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from taskbridge import task_notes
from taskbridge.database import Database, TodoistNoteMapping


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    database = Database(str(tmp_path / "test.db"))
    monkeypatch.setattr(task_notes, "db", database)
    return database


class TestGetOrCreateTaskNote:
    def test_returns_existing_mapping_without_calling_todoist(self, test_db, monkeypatch):
        test_db.create_todoist_note_mapping(
            TodoistNoteMapping(
                todoist_task_id="task-123",
                todoist_project_id="proj-1",
                note_path="/vault/note.md",
                obsidian_url="obsidian://open?vault=v&file=note.md",
            )
        )
        api_cls = MagicMock()
        monkeypatch.setattr(task_notes, "TodoistAPI", api_cls)

        mapping, is_new = task_notes.get_or_create_task_note("task-123")

        assert mapping.note_path == "/vault/note.md"
        assert is_new is False
        api_cls.assert_not_called()

    def test_creates_note_and_mapping_when_none_exists(self, test_db, monkeypatch):
        task = MagicMock(content="Write docs", project_id="proj-1", labels=["backend"])
        api = MagicMock()
        api.get_task.return_value = task
        monkeypatch.setattr(
            task_notes, "resolve_project_info", lambda project_id, api: ("taskbridge", "acme")
        )
        note_path = MagicMock()
        note_path.name = "Write docs.md"
        note_path.__str__ = lambda self: "/vault/10 Projects/taskbridge/Write docs.md"
        config_mock = MagicMock()
        config_mock.create_task_note.return_value = note_path
        config_mock.generate_obsidian_url.return_value = "obsidian://open?vault=v&file=note.md"
        monkeypatch.setattr(task_notes, "config_manager", config_mock)

        mapping, is_new = task_notes.get_or_create_task_note("task-123", api)

        assert is_new is True
        assert mapping.obsidian_url == "obsidian://open?vault=v&file=note.md"
        config_mock.create_task_note.assert_called_once_with(
            project_name="taskbridge",
            task_title="Write docs",
            client="acme",
            status="backlog",
            tags=["backend"],
        )
        api.create_comment.assert_called_once()
        stored = test_db.get_todoist_note_by_task_id("task-123")
        assert stored is not None
        assert stored.note_path == "/vault/10 Projects/taskbridge/Write docs.md"

    def test_raises_when_task_not_found(self, test_db):
        api = MagicMock()
        api.get_task.return_value = None

        with pytest.raises(task_notes.TaskNotFoundError, match="task-missing not found"):
            task_notes.get_or_create_task_note("task-missing", api)


NOV_5 = date(2026, 11, 5)


class TestEnsureDayHeading:
    """Opening a note lands it under a '# DD.Month.YYYY' heading for today (task-56)."""

    def test_heading_format(self):
        assert task_notes.day_heading(date(2026, 3, 7)) == "# 07.March.2026"

    def test_appends_heading_to_a_fresh_note(self, tmp_path):
        note = tmp_path / "n.md"
        note.write_text("---\nfileClass: task\n---\n\n")

        assert task_notes.ensure_day_heading(note, NOV_5) is True
        assert note.read_text() == "---\nfileClass: task\n---\n\n# 05.November.2026\n"

    def test_appends_after_earlier_days_with_one_blank_line(self, tmp_path):
        note = tmp_path / "n.md"
        note.write_text("---\n---\n# 03.November.2026\n- did a thing")

        task_notes.ensure_day_heading(note, NOV_5)

        assert note.read_text() == (
            "---\n---\n# 03.November.2026\n- did a thing\n\n# 05.November.2026\n"
        )

    def test_existing_heading_leaves_note_unchanged(self, tmp_path):
        note = tmp_path / "n.md"
        original = "---\n---\n# 05.November.2026 \n- first\n\n# 06.November.2026\n"
        note.write_text(original)

        assert task_notes.ensure_day_heading(note, NOV_5) is False
        assert note.read_text() == original

    def test_lower_level_heading_does_not_count(self, tmp_path):
        note = tmp_path / "n.md"
        note.write_text("## 05.November.2026\n")

        assert task_notes.ensure_day_heading(note, NOV_5) is True

    def test_missing_note_is_not_recreated(self, tmp_path):
        note = tmp_path / "moved.md"

        assert task_notes.ensure_day_heading(note, NOV_5) is False
        assert not note.exists()


class TestTaskNoteCommandHeading:
    """`taskbridge task note` adds today's heading only when it opens the note."""

    @pytest.fixture
    def note(self, tmp_path, monkeypatch):
        from taskbridge import main

        note = tmp_path / "Write docs.md"
        note.write_text("---\n---\n")
        cfg = MagicMock()
        cfg.create_task_note.return_value = note
        cfg.open_obsidian_note.return_value = True
        api = MagicMock()
        api.return_value.get_task.return_value = MagicMock(
            content="Write docs", labels=[], project_id="p1"
        )
        active = MagicMock(todoist_task_id="t1")
        monkeypatch.setattr(main, "config_manager", cfg)
        monkeypatch.setattr(main, "TodoistAPI", api)
        monkeypatch.setattr(main, "resolve_project_info", lambda pid, api: ("Docs", ""))
        monkeypatch.setattr(main.db, "get_todoist_note_by_task_id", lambda tid: None)
        monkeypatch.setattr(main.db, "create_todoist_note_mapping", lambda m: 1)
        monkeypatch.setattr(main.db, "get_active_tracking", lambda: active)
        return note

    def run(self, *args):
        from typer.testing import CliRunner

        from taskbridge.main import app

        return CliRunner().invoke(app, ["task", "note", "t1", *args])

    def test_open_adds_today_heading(self, note):
        assert self.run().exit_code == 0
        today = task_notes.day_heading(date.today())
        assert note.read_text() == f"---\n---\n\n{today}\n"

    def test_no_open_leaves_note_alone(self, note):
        assert self.run("--no-open").exit_code == 0
        assert note.read_text() == "---\n---\n"
