"""Tests for web_ui.py helpers backing the activity-note feature (task-42).

Covers the pure-Python pieces that join bartib activity rows to their Todoist
task (`_tracking_task_ids`, `_read_activities`) and the shared note
get-or-create logic (`_get_or_create_task_note`), without spinning up the
actual HTTP server.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from taskbridge import web_ui
from taskbridge.database import Database, TodoistNoteMapping


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """A real sqlite-backed Database, wired in as web_ui's module-level db."""
    database = Database(str(tmp_path / "test.db"))
    monkeypatch.setattr(web_ui, "db", database)
    return database


class TestTrackingTaskIds:
    """Tests for _tracking_task_ids."""

    def test_maps_minute_truncated_start_to_task_id(self, test_db):
        started = datetime(2026, 1, 8, 10, 0, 30, 123456)
        test_db.create_tracking_record(
            todoist_task_id="task-123",
            project_name="taskbridge",
            task_name="Write docs",
            started_at=started,
        )

        result = web_ui._tracking_task_ids(datetime(2026, 1, 1))

        assert result == {"2026-01-08T10:00:00": "task-123"}

    def test_excludes_records_outside_range(self, test_db):
        test_db.create_tracking_record(
            todoist_task_id="task-old",
            project_name="taskbridge",
            task_name="Old",
            started_at=datetime(2020, 1, 1, 9, 0),
        )

        result = web_ui._tracking_task_ids(datetime(2026, 1, 1))

        assert result == {}

    def test_ignores_records_with_no_task_id(self, test_db):
        test_db.create_tracking_record(
            todoist_task_id="",
            project_name="taskbridge",
            task_name="Ad hoc",
            started_at=datetime(2026, 1, 8, 10, 0),
        )

        result = web_ui._tracking_task_ids(datetime(2026, 1, 1))

        assert result == {}


class TestReadActivities:
    """Tests for _read_activities' todoist_task_id/note_url annotation."""

    def _write_bartib(self, tmp_path, lines):
        bartib_file = tmp_path / "activities.txt"
        bartib_file.write_text("\n".join(lines) + "\n")
        return bartib_file

    def test_annotates_activity_linked_to_a_task(self, tmp_path, monkeypatch, test_db):
        now = datetime.now()
        started = now - timedelta(hours=1)
        stopped = now - timedelta(minutes=30)
        line_start = started.strftime("%Y-%m-%d %H:%M")
        line_stop = stopped.strftime("%Y-%m-%d %H:%M")
        bartib_file = self._write_bartib(
            tmp_path, [f"{line_start} - {line_stop} | taskbridge | Write docs"]
        )
        monkeypatch.setenv("BARTIB_FILE", str(bartib_file))

        test_db.create_tracking_record(
            todoist_task_id="task-123",
            project_name="taskbridge",
            task_name="Write docs",
            started_at=datetime.strptime(line_start, "%Y-%m-%d %H:%M"),
        )
        test_db.create_todoist_note_mapping(
            TodoistNoteMapping(
                todoist_task_id="task-123",
                todoist_project_id="proj-1",
                note_path="/vault/10 Projects/taskbridge/Write docs.md",
                obsidian_url="obsidian://open?vault=v&file=Write%20docs.md",
            )
        )

        activities = web_ui._read_activities(days=7)

        assert len(activities) == 1
        assert activities[0]["todoist_task_id"] == "task-123"
        assert activities[0]["note_url"] == "obsidian://open?vault=v&file=Write%20docs.md"

    def test_activity_without_task_id_has_no_task_or_note(self, tmp_path, monkeypatch, test_db):
        now = datetime.now()
        started = now - timedelta(hours=1)
        stopped = now - timedelta(minutes=30)
        bartib_file = self._write_bartib(
            tmp_path,
            [
                f"{started.strftime('%Y-%m-%d %H:%M')} - "
                f"{stopped.strftime('%Y-%m-%d %H:%M')} | taskbridge | Untracked work"
            ],
        )
        monkeypatch.setenv("BARTIB_FILE", str(bartib_file))

        activities = web_ui._read_activities(days=7)

        assert activities[0]["todoist_task_id"] == ""
        assert activities[0]["note_url"] is None

    def test_meeting_placeholder_task_id_is_excluded(self, tmp_path, monkeypatch, test_db):
        now = datetime.now()
        started = now - timedelta(hours=1)
        stopped = now - timedelta(minutes=30)
        line_start = started.strftime("%Y-%m-%d %H:%M")
        bartib_file = self._write_bartib(
            tmp_path,
            [f"{line_start} - {stopped.strftime('%Y-%m-%d %H:%M')} | meetings | Standup"],
        )
        monkeypatch.setenv("BARTIB_FILE", str(bartib_file))

        test_db.create_tracking_record(
            todoist_task_id="meeting:standup",
            project_name="meetings",
            task_name="Standup",
            started_at=datetime.strptime(line_start, "%Y-%m-%d %H:%M"),
        )

        activities = web_ui._read_activities(days=7)

        assert activities[0]["todoist_task_id"] == ""
        assert activities[0]["note_url"] is None


class TestGetOrCreateTaskNote:
    """Tests for _get_or_create_task_note."""

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
        monkeypatch.setattr(web_ui, "TodoistAPI", api_cls)

        url, is_new = web_ui._get_or_create_task_note("task-123")

        assert url == "obsidian://open?vault=v&file=note.md"
        assert is_new is False
        api_cls.assert_not_called()

    def test_creates_note_and_mapping_when_none_exists(self, test_db, monkeypatch):
        task = MagicMock(content="Write docs", project_id="proj-1", labels=["backend"])
        api_instance = MagicMock()
        api_instance.get_task.return_value = task
        api_cls = MagicMock(return_value=api_instance)
        monkeypatch.setattr(web_ui, "TodoistAPI", api_cls)

        import taskbridge.config as config_module
        import taskbridge.main as main_module

        monkeypatch.setattr(
            main_module, "resolve_project_info", lambda project_id, api: ("taskbridge", "acme")
        )
        note_path = MagicMock()
        note_path.name = "Write docs.md"
        config_mock = MagicMock()
        config_mock.create_task_note.return_value = note_path
        config_mock.generate_obsidian_url.return_value = "obsidian://open?vault=v&file=note.md"
        monkeypatch.setattr(config_module, "config", config_mock)

        url, is_new = web_ui._get_or_create_task_note("task-123")

        assert url == "obsidian://open?vault=v&file=note.md"
        assert is_new is True
        config_mock.create_task_note.assert_called_once_with(
            project_name="taskbridge",
            task_title="Write docs",
            client="acme",
            status="backlog",
            tags=["backend"],
        )
        api_instance.create_comment.assert_called_once()
        mapping = test_db.get_todoist_note_by_task_id("task-123")
        assert mapping is not None
        assert mapping.obsidian_url == "obsidian://open?vault=v&file=note.md"

    def test_raises_when_task_not_found(self, test_db, monkeypatch):
        api_instance = MagicMock()
        api_instance.get_task.return_value = None
        monkeypatch.setattr(web_ui, "TodoistAPI", MagicMock(return_value=api_instance))

        with pytest.raises(ValueError, match="Task not found"):
            web_ui._get_or_create_task_note("task-missing")
