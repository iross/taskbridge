"""Tests for ongoing items: config storage, CLI commands, and web UI handlers."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from taskbridge import web_ui
from taskbridge.config import Config
from taskbridge.database import Database, TaskTimeTracking, is_real_todoist_task_id
from taskbridge.main import app

EMAIL = {
    "description": "Email & task management",
    "project": "Other",
    "client": "CHTC",
    "tags": [],
}


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cfg(tmp_path):
    """Config instance backed by a temp directory."""
    config = Config.__new__(Config)
    config.config_dir = tmp_path
    config.config_file = tmp_path / "config.yaml"
    config._config_data = {}
    return config


# ============================================================================
# Config
# ============================================================================


class TestOngoingConfig:
    def test_empty_by_default(self, cfg):
        assert cfg.get_templates("ongoing") == {}

    def test_set_and_get(self, cfg):
        cfg.set_template("ongoing", "email", "Email", project="Other", client="CHTC")

        assert cfg.get_templates("ongoing")["email"] == {
            "description": "Email",
            "project": "Other",
            "client": "CHTC",
            "tags": [],
        }

    def test_persists_under_separate_ongoing_key(self, cfg):
        cfg.set_template("meeting", "standup", "Daily Standup")
        cfg.set_template("ongoing", "email", "Email")

        saved = yaml.safe_load(cfg.config_file.read_text())
        assert list(saved["ongoing"]) == ["email"]
        assert list(saved["meetings"]) == ["standup"]

    def test_same_alias_in_both_kinds_is_independent(self, cfg):
        cfg.set_template("meeting", "sync", "Team sync")
        cfg.set_template("ongoing", "sync", "Inbox sync")

        assert cfg.delete_template("ongoing", "sync") is True
        assert cfg.get_templates("meeting")["sync"]["description"] == "Team sync"

    def test_delete_missing_returns_false(self, cfg):
        assert cfg.delete_template("ongoing", "nope") is False

    def test_delete_clears_usage(self, cfg):
        cfg.set_template("ongoing", "email", "Email")
        cfg.increment_template_usage("ongoing", "email")
        cfg.increment_template_usage("ongoing", "email")
        assert cfg.get_template_usage("ongoing") == {"email": 2}

        cfg.delete_template("ongoing", "email")

        assert cfg.get_template_usage("ongoing") == {}

    def test_usage_is_tracked_per_kind(self, cfg):
        cfg.increment_template_usage("ongoing", "email")

        assert cfg.get_template_usage("meeting") == {}

    def test_unknown_kind_raises(self, cfg):
        with pytest.raises(ValueError, match="Unknown template kind 'standing'"):
            cfg.get_templates("standing")


# ============================================================================
# Synthetic task IDs
# ============================================================================


class TestIsRealTodoistTaskId:
    @pytest.mark.parametrize(
        "task_id", [None, "", "meeting:standup", "cal:202610150900", "ongoing:email"]
    )
    def test_synthetic_or_empty_ids_are_not_real(self, task_id):
        assert is_real_todoist_task_id(task_id) is False

    def test_todoist_id_is_real(self):
        assert is_real_todoist_task_id("6fVMJxMmf2gvcCXq") is True

    @patch("taskbridge.web_ui.TodoistAPI")
    @patch("taskbridge.web_ui.BartibIntegration")
    def test_stopping_ongoing_entry_does_not_comment_on_todoist(self, _bartib, todoist, tmp_path):
        database = Database(str(tmp_path / "test.db"))
        tracking = TaskTimeTracking(
            id=1, todoist_task_id="ongoing:email", started_at=datetime(2026, 10, 15, 8, 0)
        )
        with patch.object(web_ui, "db", database):
            web_ui._stop_active(tracking)

        todoist.assert_not_called()


# ============================================================================
# CLI
# ============================================================================


class TestOngoingCli:
    @patch("taskbridge.main.config_manager")
    def test_define(self, mock_cfg, runner):
        result = runner.invoke(
            app, ["ongoing", "define", "email", "-d", "Email", "-p", "Other", "-c", "CHTC"]
        )

        assert result.exit_code == 0
        assert "CHTC::Other" in result.output
        mock_cfg.set_template.assert_called_once_with(
            "ongoing", alias="email", description="Email", project="Other", client="CHTC", tags=[]
        )

    @patch("taskbridge.main.config_manager")
    def test_list_empty(self, mock_cfg, runner):
        mock_cfg.get_templates.return_value = {}

        result = runner.invoke(app, ["ongoing", "list"])

        assert result.exit_code == 0
        assert "No ongoing items defined" in result.output

    @patch("taskbridge.main.config_manager")
    def test_list_uses_default_project_when_unset(self, mock_cfg, runner):
        mock_cfg.get_templates.return_value = {
            "focus": {"description": "Morning focus", "project": "", "client": "", "tags": []}
        }

        result = runner.invoke(app, ["ongoing", "list"])

        assert result.exit_code == 0
        assert "Morning focus" in result.output
        assert "Bartib      : ongoing" in result.output

    @patch("taskbridge.main.config_manager")
    def test_undefine_missing_exits_nonzero(self, mock_cfg, runner):
        mock_cfg.delete_template.return_value = False

        result = runner.invoke(app, ["ongoing", "undefine", "nope"])

        assert result.exit_code == 1
        assert "No ongoing item named 'nope'" in result.output
        mock_cfg.delete_template.assert_called_once_with("ongoing", "nope")

    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.config_manager")
    def test_start_unknown_alias_fails_without_tracking(self, mock_cfg, mock_bartib, runner):
        mock_cfg.get_templates.return_value = {}

        result = runner.invoke(app, ["ongoing", "start", "nope"])

        assert result.exit_code == 1
        assert "No ongoing item named 'nope'" in result.output
        mock_bartib.return_value.start_tracking.assert_not_called()

    @patch("taskbridge.main.db")
    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.config_manager")
    def test_start_tracks_with_ongoing_tag(self, mock_cfg, mock_bartib, mock_db, runner):
        mock_cfg.get_templates.return_value = {"email": EMAIL}
        mock_db.get_active_tracking.return_value = None

        result = runner.invoke(app, ["ongoing", "start", "email"])

        assert result.exit_code == 0
        mock_bartib.return_value.start_tracking.assert_called_once_with(
            description="Email & task management #ongoing", project="CHTC::Other"
        )
        record = mock_db.create_tracking_record.call_args.kwargs
        assert record["todoist_task_id"] == "ongoing:email"
        mock_cfg.increment_template_usage.assert_called_once_with("ongoing", "email")

    @patch("taskbridge.main.db")
    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.config_manager")
    def test_start_does_not_duplicate_ongoing_tag(self, mock_cfg, mock_bartib, mock_db, runner):
        mock_cfg.get_templates.return_value = {"email": {**EMAIL, "tags": ["ongoing", "admin"]}}
        mock_db.get_active_tracking.return_value = None

        runner.invoke(app, ["ongoing", "start", "email"])

        description = mock_bartib.return_value.start_tracking.call_args.kwargs["description"]
        assert description == "Email & task management #ongoing #admin"

    @patch("taskbridge.main.db")
    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.config_manager")
    def test_start_stops_active_tracking(self, mock_cfg, _bartib, mock_db, runner):
        mock_cfg.get_templates.return_value = {"email": EMAIL}
        active = TaskTimeTracking(id=1, todoist_task_id="abc", task_name="Prev", project_name="X")
        mock_db.get_active_tracking.return_value = active

        with patch("taskbridge.main.stop_tracking_internal", return_value=(True, 60)) as stop:
            result = runner.invoke(app, ["ongoing", "start", "email"])

        assert result.exit_code == 0
        stop.assert_called_once_with(active)


# ============================================================================
# Web UI handlers
# ============================================================================


@pytest.fixture
def handler():
    """A TimeWebHandler with no socket; responses are captured on _send_json."""
    h = web_ui.TimeWebHandler.__new__(web_ui.TimeWebHandler)
    h._send_json = MagicMock()
    return h


@pytest.fixture
def web_cfg(cfg, monkeypatch):
    monkeypatch.setattr("taskbridge.config.config", cfg)
    return cfg


@pytest.fixture
def web_db(tmp_path, monkeypatch):
    database = Database(str(tmp_path / "test.db"))
    monkeypatch.setattr(web_ui, "db", database)
    return database


def response(handler):
    args = handler._send_json.call_args.args
    return args[0], (args[1] if len(args) > 1 else 200)


class TestOngoingWebHandlers:
    def test_kind_from_path(self):
        assert web_ui._template_kind_from_path("/api/ongoing/start") == "ongoing"
        assert web_ui._template_kind_from_path("/api/meeting/define") == "meeting"

    def test_list_orders_by_usage(self, handler, web_cfg):
        web_cfg.set_template("ongoing", "email", "Email")
        web_cfg.set_template("ongoing", "focus", "Morning focus")
        web_cfg.increment_template_usage("ongoing", "focus")

        handler._handle_templates_list("ongoing")

        payload, _ = response(handler)
        assert [item["alias"] for item in payload["ongoing"]] == ["focus", "email"]

    def test_meeting_list_keeps_meetings_key(self, handler, web_cfg):
        web_cfg.set_template("meeting", "standup", "Standup")

        handler._handle_templates_list("meeting")

        payload, _ = response(handler)
        assert payload["meetings"][0]["alias"] == "standup"

    def test_define_requires_alias_and_description(self, handler, web_cfg):
        handler._handle_template_define("ongoing", {"alias": "email"})

        payload, status = response(handler)
        assert status == 400
        assert web_cfg.get_templates("ongoing") == {}

    def test_define_saves_parsed_tags(self, handler, web_cfg):
        handler._handle_template_define(
            "ongoing", {"alias": "email", "description": "Email", "tags": "admin, inbox ,"}
        )

        assert response(handler)[0] == {"success": True}
        assert web_cfg.get_templates("ongoing")["email"]["tags"] == ["admin", "inbox"]

    def test_undefine_missing_returns_404(self, handler, web_cfg):
        handler._handle_template_undefine("ongoing", {"alias": "nope"})

        payload, status = response(handler)
        assert status == 404
        assert payload["error"] == "No ongoing item named 'nope'"

    def test_start_requires_alias(self, handler, web_cfg):
        handler._handle_template_start("ongoing", {"alias": "  "})

        assert response(handler)[1] == 400

    def test_start_unknown_alias_returns_404(self, handler, web_cfg):
        handler._handle_template_start("ongoing", {"alias": "nope"})

        payload, status = response(handler)
        assert status == 404
        assert payload["error"] == "No ongoing item named 'nope'"

    @patch("taskbridge.web_ui.BartibIntegration")
    def test_start_records_synthetic_id_and_usage(self, mock_bartib, handler, web_cfg, web_db):
        web_cfg.set_template("ongoing", "Post Outage", "Post-outage catchup", client="CHTC")

        handler._handle_template_start("ongoing", {"alias": "Post Outage"})

        assert response(handler)[0] == {"success": True, "project": "CHTC::ongoing"}
        mock_bartib.return_value.start_tracking.assert_called_once_with(
            description="Post-outage catchup #ongoing", project="CHTC::ongoing"
        )
        active = web_db.get_active_tracking()
        assert active is not None
        assert active.todoist_task_id == "ongoing:post-outage"
        assert web_cfg.get_template_usage("ongoing") == {"Post Outage": 1}

    @patch("taskbridge.web_ui.BartibIntegration")
    def test_start_stops_active_tracking(self, _bartib, handler, web_cfg, web_db):
        web_cfg.set_template("ongoing", "email", "Email")
        web_db.create_tracking_record(
            todoist_task_id="meeting:standup",
            project_name="meetings",
            task_name="Standup",
            started_at=datetime.now(),
        )

        with patch.object(web_ui, "_stop_active") as stop:
            handler._handle_template_start("ongoing", {"alias": "email"})

        stop.assert_called_once()
        assert stop.call_args.args[0].todoist_task_id == "meeting:standup"

    def test_page_has_ongoing_button(self):
        assert '<button id="btn-ongoing"' in web_ui.HTML
        assert "&infin; Ongoing" in web_ui.HTML
