"""Tests for meeting time tracking commands and config."""

from datetime import datetime
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from taskbridge.main import app


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config(tmp_path):
    """Config instance backed by a temp directory."""
    from taskbridge.config import Config

    cfg = Config.__new__(Config)
    cfg.config_dir = tmp_path
    cfg.config_file = tmp_path / "config.yaml"
    cfg._config_data = {}
    return cfg


# ============================================================================
# Config: get/set/delete meetings
# ============================================================================


class TestMeetingConfig:
    def test_get_meetings_empty(self, mock_config):
        assert mock_config.get_meetings() == {}

    def test_set_meeting_basic(self, mock_config):
        mock_config.set_meeting("standup", "Daily Standup")

        meetings = mock_config.get_meetings()
        assert "standup" in meetings
        assert meetings["standup"]["description"] == "Daily Standup"
        assert meetings["standup"]["project"] == ""
        assert meetings["standup"]["client"] == ""
        assert meetings["standup"]["tags"] == []

    def test_set_meeting_full(self, mock_config):
        mock_config.set_meeting(
            "standup",
            "Daily Standup",
            project="webapp",
            client="acme",
            tags=["standup", "recurring"],
        )

        m = mock_config.get_meetings()["standup"]
        assert m["project"] == "webapp"
        assert m["client"] == "acme"
        assert m["tags"] == ["standup", "recurring"]

    def test_set_meeting_overwrites(self, mock_config):
        mock_config.set_meeting("standup", "Old Description")
        mock_config.set_meeting("standup", "New Description", project="proj")

        m = mock_config.get_meetings()["standup"]
        assert m["description"] == "New Description"
        assert m["project"] == "proj"

    def test_delete_meeting_exists(self, mock_config):
        mock_config.set_meeting("standup", "Daily Standup")

        result = mock_config.delete_meeting("standup")

        assert result is True
        assert "standup" not in mock_config.get_meetings()

    def test_delete_meeting_not_found(self, mock_config):
        result = mock_config.delete_meeting("nonexistent")

        assert result is False

    def test_multiple_meetings_independent(self, mock_config):
        mock_config.set_meeting("standup", "Daily Standup")
        mock_config.set_meeting("retro", "Sprint Retro", client="acme")

        meetings = mock_config.get_meetings()
        assert len(meetings) == 2
        assert "standup" in meetings
        assert "retro" in meetings


# ============================================================================
# CLI: meeting define / list / undefine / start
# ============================================================================


class TestMeetingDefineCommand:
    @patch("taskbridge.main.config_manager")
    def test_define_creates_meeting(self, mock_cfg, runner):
        mock_cfg.get_meetings.return_value = {}

        args = [
            "meeting",
            "define",
            "standup",
            "-d",
            "Daily Standup",
            "-p",
            "webapp",
            "-c",
            "acme",
            "-t",
            "standup,recurring",
        ]
        result = runner.invoke(app, args)

        assert result.exit_code == 0
        mock_cfg.set_meeting.assert_called_once_with(
            alias="standup",
            description="Daily Standup",
            project="webapp",
            client="acme",
            tags=["standup", "recurring"],
        )

    @patch("taskbridge.main.config_manager")
    def test_define_shows_bartib_project(self, mock_cfg, runner):
        mock_cfg.get_meetings.return_value = {}

        result = runner.invoke(
            app,
            ["meeting", "define", "standup", "-d", "Daily Standup", "-c", "acme", "-t", "standup"],
        )

        assert result.exit_code == 0
        assert "acme::meetings::standup" in result.output  # define preview doesn't add tag

    @patch("taskbridge.main.config_manager")
    def test_define_minimal(self, mock_cfg, runner):
        """Define with only required args — description."""
        mock_cfg.get_meetings.return_value = {}

        result = runner.invoke(app, ["meeting", "define", "focus", "-d", "Focus block"])

        assert result.exit_code == 0
        mock_cfg.set_meeting.assert_called_once_with(
            alias="focus",
            description="Focus block",
            project="",
            client="",
            tags=[],
        )


class TestMeetingListCommand:
    @patch("taskbridge.main.config_manager")
    def test_list_empty(self, mock_cfg, runner):
        mock_cfg.get_meetings.return_value = {}

        result = runner.invoke(app, ["meeting", "list"])

        assert result.exit_code == 0
        assert "No recurring meetings" in result.output

    @patch("taskbridge.main.config_manager")
    def test_list_shows_meetings(self, mock_cfg, runner):
        mock_cfg.get_meetings.return_value = {
            "standup": {
                "description": "Daily Standup",
                "project": "webapp",
                "client": "acme",
                "tags": ["standup"],
            }
        }

        result = runner.invoke(app, ["meeting", "list"])

        assert result.exit_code == 0
        assert "standup" in result.output
        assert "Daily Standup" in result.output
        assert "acme::webapp::standup" in result.output


class TestMeetingUndefineCommand:
    @patch("taskbridge.main.config_manager")
    def test_undefine_success(self, mock_cfg, runner):
        mock_cfg.delete_meeting.return_value = True

        result = runner.invoke(app, ["meeting", "undefine", "standup"])

        assert result.exit_code == 0
        assert "Removed" in result.output

    @patch("taskbridge.main.config_manager")
    def test_undefine_not_found(self, mock_cfg, runner):
        mock_cfg.delete_meeting.return_value = False

        result = runner.invoke(app, ["meeting", "undefine", "nonexistent"])

        assert result.exit_code != 0
        assert "No meeting named" in result.output


class TestMeetingStartCommand:
    @patch("taskbridge.main.db")
    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.config_manager")
    def test_start_named_meeting(self, mock_cfg, mock_bartib_cls, mock_db, runner):
        """Starting a defined alias uses stored definition."""
        mock_cfg.get_meetings.return_value = {
            "standup": {
                "description": "Daily Standup",
                "project": "webapp",
                "client": "acme",
                "tags": ["standup"],
            }
        }
        mock_db.get_active_tracking.return_value = None

        with patch("taskbridge.main.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 25, 9, 0, 0)
            result = runner.invoke(app, ["meeting", "start", "standup"])

        assert result.exit_code == 0
        mock_bartib_cls.return_value.start_tracking.assert_called_once_with(
            description="Daily Standup",
            project="acme::webapp::standup,meeting",
        )
        assert "Daily Standup" in result.output
        assert "(recurring: standup)" in result.output

    @patch("taskbridge.main.db")
    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.config_manager")
    def test_start_adhoc_meeting(self, mock_cfg, mock_bartib_cls, mock_db, runner):
        """Unrecognised name is treated as ad-hoc description."""
        mock_cfg.get_meetings.return_value = {}
        mock_db.get_active_tracking.return_value = None

        with patch("taskbridge.main.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 25, 9, 0, 0)
            result = runner.invoke(app, ["meeting", "start", "1:1 with Bob", "-c", "acme"])

        assert result.exit_code == 0
        mock_bartib_cls.return_value.start_tracking.assert_called_once_with(
            description="1:1 with Bob",
            project="acme::meetings::meeting",
        )

    @patch("taskbridge.main.db")
    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.config_manager")
    def test_start_stops_active_tracking(self, mock_cfg, mock_bartib_cls, mock_db, runner):
        """Starting a meeting stops any currently running activity."""
        from taskbridge.database import TaskTimeTracking

        mock_cfg.get_meetings.return_value = {}
        active = TaskTimeTracking(
            id=1,
            todoist_task_id="task-123",
            project_name="acme::webapp",
            task_name="Previous task",
            started_at=datetime(2026, 2, 25, 8, 0, 0),
        )
        mock_db.get_active_tracking.return_value = active

        with (
            patch("taskbridge.main.stop_tracking_internal", return_value=(True, 3600)) as mock_stop,
            patch("taskbridge.main.datetime") as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2026, 2, 25, 9, 0, 0)
            result = runner.invoke(app, ["meeting", "start", "Standup"])

        assert result.exit_code == 0
        mock_stop.assert_called_once_with(active)
        assert "Stopping" in result.output

    @patch("taskbridge.main.db")
    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.config_manager")
    def test_start_uses_meetings_as_default_project(
        self, mock_cfg, mock_bartib_cls, mock_db, runner
    ):
        """Ad-hoc meeting with no project uses 'meetings' as bartib project."""
        mock_cfg.get_meetings.return_value = {}
        mock_db.get_active_tracking.return_value = None

        with patch("taskbridge.main.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 25, 9, 0, 0)
            result = runner.invoke(app, ["meeting", "start", "Team sync"])

        assert result.exit_code == 0
        mock_bartib_cls.return_value.start_tracking.assert_called_once_with(
            description="Team sync",
            project="meetings::meeting",
        )

    @patch("taskbridge.main.db")
    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.config_manager")
    def test_start_cli_flags_override_definition(self, mock_cfg, mock_bartib_cls, mock_db, runner):
        """CLI flags take precedence over the stored definition."""
        mock_cfg.get_meetings.return_value = {
            "standup": {
                "description": "Daily Standup",
                "project": "webapp",
                "client": "acme",
                "tags": ["standup"],
            }
        }
        mock_db.get_active_tracking.return_value = None

        with patch("taskbridge.main.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 25, 9, 0, 0)
            result = runner.invoke(app, ["meeting", "start", "standup", "-c", "other-client"])

        assert result.exit_code == 0
        call_kwargs = mock_bartib_cls.return_value.start_tracking.call_args[1]
        assert "other-client" in call_kwargs["project"]

    @patch("taskbridge.main.db")
    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.config_manager")
    def test_start_saves_db_record(self, mock_cfg, mock_bartib_cls, mock_db, runner):
        """Starting a meeting saves a record to the DB."""
        mock_cfg.get_meetings.return_value = {}
        mock_db.get_active_tracking.return_value = None

        with patch("taskbridge.main.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 25, 9, 0, 0)
            runner.invoke(app, ["meeting", "start", "Retro"])

        mock_db.create_tracking_record.assert_called_once()
        call_kwargs = mock_db.create_tracking_record.call_args[1]
        assert call_kwargs["todoist_task_id"].startswith("meeting:")
        assert call_kwargs["task_name"] == "Retro"
