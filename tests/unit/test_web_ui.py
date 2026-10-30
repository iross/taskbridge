"""Tests for web_ui.py helpers backing the activity-note feature (task-42).

Covers the pure-Python pieces that join bartib activity rows to their Todoist
task (`_tracking_task_ids`, `_read_activities`), without spinning up the
actual HTTP server.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from taskbridge import web_ui
from taskbridge.database import Database, TodoistNoteMapping
from taskbridge.todoist_api import TodoistProject


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


def _act(start: str, stop: str | None) -> dict:
    _act.line_no = getattr(_act, "line_no", 0) + 1
    return {
        "line_no": _act.line_no,
        "started_at": f"2026-01-08T{start}:00",
        "stopped_at": stop and f"2026-01-08T{stop}:00",
    }


class TestMarkOverlaps:
    """Tests for _mark_overlaps."""

    NOW = datetime(2026, 1, 8, 12, 0)

    def test_overlapping_pair_points_at_each_other(self):
        a, b = _act("09:00", "10:00"), _act("09:30", "10:30")
        web_ui._mark_overlaps([a, b], now=self.NOW)
        assert a["overlaps"] == [b["line_no"]]
        assert b["overlaps"] == [a["line_no"]]

    def test_back_to_back_entries_do_not_overlap(self):
        a, b = _act("09:00", "10:00"), _act("10:00", "11:00")
        web_ui._mark_overlaps([a, b], now=self.NOW)
        assert a["overlaps"] == []
        assert b["overlaps"] == []

    def test_entry_inside_a_long_one_overlaps_it_but_not_its_neighbours(self):
        long = _act("09:00", "11:00")
        first, second = _act("09:15", "09:30"), _act("10:00", "10:30")
        web_ui._mark_overlaps([second, long, first], now=self.NOW)
        assert sorted(long["overlaps"]) == sorted([first["line_no"], second["line_no"]])
        assert first["overlaps"] == [long["line_no"]]
        assert second["overlaps"] == [long["line_no"]]

    def test_running_entry_ends_at_now(self):
        running = _act("11:00", None)
        before_now, after_now = _act("11:30", "11:45"), _act("12:00", "12:30")
        web_ui._mark_overlaps([running, before_now, after_now], now=self.NOW)
        assert running["overlaps"] == [before_now["line_no"]]
        assert after_now["overlaps"] == []

    def test_empty_list(self):
        web_ui._mark_overlaps([], now=self.NOW)

    def test_entries_sharing_a_start_time_are_told_apart(self):
        a, b = _act("09:00", "10:00"), _act("09:00", "10:00")
        web_ui._mark_overlaps([a, b], now=self.NOW)
        assert a["overlaps"] == [b["line_no"]]
        assert b["overlaps"] == [a["line_no"]]


SAME_START = [
    "2026-01-08 09:00 - 2026-01-08 10:00 | meetings | Stub",
    "",
    "2026-01-08 09:00 - 2026-01-08 10:00 | meetings | Stub",
    "2026-01-08 09:00 - 2026-01-08 10:00 | meetings | Stub",
    "2026-01-08 11:00 | work | Running",
]
NINE = "2026-01-08T09:00:00"


@pytest.fixture
def bartib_file(tmp_path, monkeypatch):
    path = tmp_path / "activities.txt"
    path.write_text("\n".join(SAME_START) + "\n")
    monkeypatch.setenv("BARTIB_FILE", str(path))
    return path


class TestEditBartibLine:
    """Tests for _edit_bartib_line, which addresses entries by line number."""

    def _edit(self, line_no, started_at=NINE, **changes):
        fields = {"new_started_at": "", "new_stopped_at": "", "project": "meetings"}
        fields["description"] = "Stub"
        fields.update(changes)
        return web_ui._edit_bartib_line(line_no, started_at, **fields)

    def test_edits_only_the_addressed_entry_among_same_start_ones(self, bartib_file):
        assert self._edit(2, description="Standup", new_stopped_at="2026-01-08T09:30")
        lines = bartib_file.read_text().splitlines()
        assert lines[0] == SAME_START[0]
        assert lines[2] == "2026-01-08 09:00 - 2026-01-08 09:30 | meetings | Standup"
        assert lines[3] == SAME_START[3]

    def test_keeps_a_running_entry_running(self, bartib_file):
        assert self._edit(4, "2026-01-08T11:00:00", new_started_at="2026-01-08T10:45")
        assert bartib_file.read_text().splitlines()[4] == "2026-01-08 10:45 | meetings | Stub"

    def test_refuses_when_line_no_longer_matches_start(self, bartib_file):
        assert not self._edit(4)
        assert not self._edit(1)
        assert not self._edit(99)
        assert bartib_file.read_text().splitlines() == SAME_START

    def test_no_bartib_file_configured(self, monkeypatch):
        monkeypatch.delenv("BARTIB_FILE", raising=False)
        assert not self._edit(0)


class TestDeleteBartibLine:
    """Tests for _delete_bartib_line."""

    def test_deletes_only_the_addressed_entry(self, bartib_file):
        assert web_ui._delete_bartib_line(3, NINE)
        assert bartib_file.read_text().splitlines() == SAME_START[:3] + SAME_START[4:]

    def test_refuses_when_line_no_longer_matches_start(self, bartib_file):
        assert not web_ui._delete_bartib_line(4, NINE)
        assert not web_ui._delete_bartib_line(-1, NINE)
        assert bartib_file.read_text().splitlines() == SAME_START


class TestRunningBartibLineNo:
    """Tests for _running_bartib_line_no."""

    def test_finds_the_unstopped_entry(self):
        assert web_ui._running_bartib_line_no(SAME_START, "2026-01-08T11:00:00") == 4

    def test_ignores_stopped_entries_with_that_start(self):
        assert web_ui._running_bartib_line_no(SAME_START, NINE) is None


class TestReadActivitiesLineNumbers:
    """_read_activities gives same-start entries distinct line numbers."""

    def test_line_numbers_match_file_positions(self, tmp_path, monkeypatch, test_db):
        start = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        stop = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")
        path = tmp_path / "activities.txt"
        path.write_text(f"{start} - {stop} | m | A\n\n{start} - {stop} | m | B\n")
        monkeypatch.setenv("BARTIB_FILE", str(path))

        by_desc = {a["description"]: a["line_no"] for a in web_ui._read_activities(days=7)}

        assert by_desc == {"A": 0, "B": 2}


class TestKnownTags:
    """Tests for the tag list backing the start-form/edit-modal tag picker."""

    @pytest.fixture
    def tag_colors(self, monkeypatch):
        cfg = MagicMock()
        cfg.get_tag_colors.return_value = {}
        monkeypatch.setattr("taskbridge.config.config", cfg)
        return cfg.get_tag_colors

    def _log(self, tmp_path, monkeypatch, lines):
        path = tmp_path / "activities.bartib"
        path.write_text("\n".join(lines) + "\n")
        monkeypatch.setenv("BARTIB_FILE", str(path))

    def test_counts_tags_across_whole_log_most_used_first(self, tmp_path, monkeypatch, tag_colors):
        self._log(
            tmp_path,
            monkeypatch,
            [
                "# February 2026",
                "2025-01-02 09:00 - 2025-01-02 09:30 | CHTC | Old standup #meeting",
                "2026-10-15 09:00 - 2026-10-15 09:30 | CHTC | Standup #meeting #meeting",
                "2026-10-15 10:00 - 2026-10-15 11:00 | CHTC | GPU report #reporting #k8s",
                "2026-10-15 11:00 | CHTC | Cluster work #k8s",
                "not a bartib line",
            ],
        )

        assert web_ui._known_tags() == ["k8s", "meeting", "reporting"]
        assert web_ui._read_tag_counts() == {"meeting": 2, "reporting": 1, "k8s": 2}

    def test_lone_hash_is_not_a_tag(self, tmp_path, monkeypatch, tag_colors):
        self._log(tmp_path, monkeypatch, ["2026-10-15 09:00 | CHTC | Fix issue # 12"])

        assert web_ui._known_tags() == []

    def test_includes_color_only_tags_without_duplicating_case(
        self, tmp_path, monkeypatch, tag_colors
    ):
        self._log(tmp_path, monkeypatch, ["2026-10-15 09:00 | CHTC | GPU work #GPUs"])
        tag_colors.return_value = {"gpus": "#ff0000", "admin": "#00ff00"}

        assert web_ui._known_tags() == ["GPUs", "admin"]

    def test_no_bartib_file_configured(self, monkeypatch, tag_colors):
        monkeypatch.delenv("BARTIB_FILE", raising=False)

        assert web_ui._known_tags() == []

    def test_unreadable_log_returns_error_response(self, tmp_path, monkeypatch, tag_colors):
        monkeypatch.setenv("BARTIB_FILE", str(tmp_path / "missing.bartib"))
        handler = web_ui.TimeWebHandler.__new__(web_ui.TimeWebHandler)
        handler._send_json = MagicMock()

        handler._handle_tags()

        payload, status = handler._send_json.call_args.args
        assert status == 500
        assert payload["tags"] == []
        assert "Could not read bartib log" in payload["error"]


class TestTodoistProjectBartibStrings:
    """/api/projects gives each Todoist project the bartib string a start would log."""

    @pytest.fixture
    def todoist(self, monkeypatch):
        api = MagicMock()
        monkeypatch.setattr(web_ui, "TodoistAPI", lambda: api)
        cfg = MagicMock()
        cfg.get_todoist_project_mappings.return_value = {}
        monkeypatch.setattr("taskbridge.config.config", cfg)
        return api, cfg.get_todoist_project_mappings

    def _project(self, pid, name, parent=None, **kw):
        return TodoistProject(id=pid, name=name, color="", parent_id=parent, **kw)

    def test_root_ancestor_is_client_at_any_depth(self, todoist):
        api, _ = todoist
        api.get_projects.return_value = [
            self._project("1", "PATh"),
            self._project("2", "Monthly Report", parent="1"),
            self._project("3", "Draft 🚧", parent="2"),
            self._project("9", "Inbox", is_inbox_project=True),
        ]

        projects = web_ui._get_todoist_projects()

        assert [(p["name"], p["bartib"]) for p in projects] == [
            ("PATh", "PATh"),
            ("PATh / Monthly Report", "PATh::Monthly-Report"),
            ("PATh / Monthly Report / Draft 🚧", "PATh::Draft"),
        ]

    def test_manual_mapping_wins(self, todoist):
        api, mappings = todoist
        api.get_projects.return_value = [
            self._project("1", "PATh"),
            self._project("2", "Monthly Report", parent="1"),
        ]
        mappings.return_value = {"2": {"client": "OSG", "folder": "Reports"}}

        projects = web_ui._get_todoist_projects()

        assert projects[1]["bartib"] == "OSG::Reports"

    def test_todoist_failure_returns_empty_list(self, todoist):
        api, _ = todoist
        api.get_projects.side_effect = RuntimeError("offline")

        assert web_ui._get_todoist_projects() == []


class TestActivityEditReassignsProject:
    """Editing an entry's project in the modal, for stopped and running entries."""

    LOG = [
        "2026-01-08 09:00 - 2026-01-08 10:00 | Inbox | Report",
        "2026-01-08 11:00 | Inbox | Report",
    ]

    @pytest.fixture
    def log(self, tmp_path, monkeypatch):
        path = tmp_path / "activities.txt"
        path.write_text("\n".join(self.LOG) + "\n")
        monkeypatch.setenv("BARTIB_FILE", str(path))
        return path

    @pytest.fixture
    def running(self, test_db):
        test_db.create_tracking_record(
            todoist_task_id="t1",
            project_name="Inbox",
            task_name="Report",
            started_at=datetime(2026, 1, 8, 11, 0, 42),
        )
        return test_db

    def _edit(self, line_no, started_at, **changes):
        handler = web_ui.TimeWebHandler.__new__(web_ui.TimeWebHandler)
        handler._send_json = MagicMock()
        body = {
            "line_no": line_no,
            "original_started_at": started_at,
            "new_started_at": "",
            "new_stopped_at": "",
            "project": "PATh::Monthly_Report",
            "description": "Report",
        }
        body.update(changes)
        handler._handle_activity_edit(body)
        return handler._send_json.call_args.args[0]

    def test_stopped_entry_moves_without_touching_running_record(self, log, running):
        assert self._edit(0, "2026-01-08T09:00:00")["success"]

        lines = log.read_text().splitlines()
        assert lines[0] == "2026-01-08 09:00 - 2026-01-08 10:00 | PATh::Monthly_Report | Report"
        assert running.get_active_tracking().project_name == "Inbox"

    def test_running_entry_moves_in_log_and_tracking_record(self, log, running):
        assert self._edit(1, "2026-01-08T11:00:00", description="Report #draft")["success"]

        assert (
            log.read_text().splitlines()[1]
            == "2026-01-08 11:00 | PATh::Monthly_Report | Report #draft"
        )
        active = running.get_active_tracking()
        assert (active.project_name, active.task_name) == ("PATh::Monthly_Report", "Report #draft")
        assert active.started_at == datetime(2026, 1, 8, 11, 0, 42)

    def test_running_entry_start_change_reaches_tracking_record(self, log, running):
        self._edit(1, "2026-01-08T11:00:00", new_started_at="2026-01-08T10:45")

        assert running.get_active_tracking().started_at == datetime(2026, 1, 8, 10, 45)

    def test_no_active_record_still_edits_log(self, log, test_db):
        assert self._edit(1, "2026-01-08T11:00:00")["success"]

        assert log.read_text().splitlines()[1] == "2026-01-08 11:00 | PATh::Monthly_Report | Report"

    def test_stopped_entry_sharing_running_start_leaves_record_alone(self, log, running):
        log.write_text(
            "2026-01-08 11:00 - 2026-01-08 11:05 | Inbox | Report\n"
            "2026-01-08 11:00 | Inbox | Report\n"
        )

        assert self._edit(0, "2026-01-08T11:00:00")["success"]

        assert running.get_active_tracking().project_name == "Inbox"
