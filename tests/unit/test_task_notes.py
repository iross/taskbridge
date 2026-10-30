"""Tests for task_notes.get_or_create_task_note, shared by the web UI and backlog archive."""

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
