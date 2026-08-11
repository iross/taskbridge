"""Unit tests for cross-tool inbox scanning (ADR-002)."""

import os
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from taskbridge.inbox import (
    InboxItem,
    enabled_modules,
    group_by_label,
    scan_all,
    scan_obsidian_folders,
    scan_todoist_inbox,
)
from taskbridge.main import app


@pytest.fixture
def vault_config(tmp_path):
    """Mock config manager pointed at a temporary vault."""
    config = Mock()
    config.get_obsidian_vault_path.return_value = str(tmp_path)
    config.generate_obsidian_file_url.side_effect = lambda rel_path: (
        f"obsidian://open?vault=test-vault&file={rel_path.replace(' ', '%20')}"
    )
    return config


def touch_with_age(path, age_days):
    """Create a file and backdate its mtime by age_days."""
    path.write_text("test note")
    mtime = time.time() - (age_days * 86400)
    os.utime(path, (mtime, mtime))


class TestScanObsidianFolders:
    """Tests for scan_obsidian_folders."""

    def test_empty_folder_returns_no_items(self, tmp_path, vault_config):
        (tmp_path / "00 Inbox").mkdir()
        items = scan_obsidian_folders([{"label": "inbox", "path": "00 Inbox"}], vault_config)
        assert items == []

    def test_stale_item_age_is_computed_from_mtime(self, tmp_path, vault_config):
        inbox = tmp_path / "00 Inbox"
        inbox.mkdir()
        touch_with_age(inbox / "Old Note.md", age_days=10)

        items = scan_obsidian_folders([{"label": "inbox", "path": "00 Inbox"}], vault_config)

        assert len(items) == 1
        assert items[0].label == "inbox"
        assert items[0].age_days == pytest.approx(10, abs=0.01)

    def test_missing_folder_is_skipped_not_fatal(self, tmp_path, vault_config):
        items = scan_obsidian_folders([{"label": "inbox", "path": "does-not-exist"}], vault_config)
        assert items == []

    def test_no_vault_path_configured_returns_no_items(self, vault_config):
        vault_config.get_obsidian_vault_path.return_value = None
        items = scan_obsidian_folders([{"label": "inbox", "path": "00 Inbox"}], vault_config)
        assert items == []

    def test_multiple_configured_folders_are_all_scanned(self, tmp_path, vault_config):
        inbox = tmp_path / "00 Inbox"
        inbox.mkdir()
        touch_with_age(inbox / "Note.md", age_days=1)

        literature = tmp_path / "30 Resources" / "37 Literature"
        literature.mkdir(parents=True)
        touch_with_age(literature / "Highlight.md", age_days=2)

        items = scan_obsidian_folders(
            [
                {"label": "inbox", "path": "00 Inbox"},
                {"label": "literature", "path": "30 Resources/37 Literature"},
            ],
            vault_config,
        )

        labels = sorted(item.label for item in items)
        assert labels == ["inbox", "literature"]

    def test_item_includes_obsidian_uri(self, tmp_path, vault_config):
        inbox = tmp_path / "00 Inbox"
        inbox.mkdir()
        touch_with_age(inbox / "Note.md", age_days=1)

        items = scan_obsidian_folders([{"label": "inbox", "path": "00 Inbox"}], vault_config)

        assert len(items) == 1
        vault_config.generate_obsidian_file_url.assert_called_once_with("00 Inbox/Note.md")
        assert items[0].uri.startswith("obsidian://open?vault=test-vault")


class TestEnabledModules:
    """Tests for enabled_modules."""

    def test_returns_obsidian_inbox_when_enabled(self, vault_config):
        vault_config.is_module_enabled.side_effect = lambda name, profile=None: (
            name == "obsidian_inbox"
        )
        assert enabled_modules(vault_config, profile="home") == ["obsidian_inbox"]

    def test_empty_when_nothing_enabled(self, vault_config):
        vault_config.is_module_enabled.return_value = False
        assert enabled_modules(vault_config, profile="home") == []


class TestScanAll:
    """Tests for scan_all."""

    def test_scans_obsidian_when_enabled(self, tmp_path, vault_config):
        vault_config.is_module_enabled.side_effect = lambda name, profile=None: (
            name == "obsidian_inbox"
        )
        vault_config.get_inbox_folders.return_value = [{"label": "inbox", "path": "00 Inbox"}]
        inbox_dir = tmp_path / "00 Inbox"
        inbox_dir.mkdir()
        touch_with_age(inbox_dir / "Note.md", age_days=1)

        items = scan_all(vault_config, profile="home")

        assert len(items) == 1
        assert items[0].label == "inbox"

    def test_skips_obsidian_when_disabled(self, tmp_path, vault_config):
        vault_config.is_module_enabled.return_value = False
        vault_config.get_inbox_folders.return_value = [{"label": "inbox", "path": "00 Inbox"}]
        inbox_dir = tmp_path / "00 Inbox"
        inbox_dir.mkdir()
        touch_with_age(inbox_dir / "Note.md", age_days=1)

        assert scan_all(vault_config, profile="home") == []

    @patch("taskbridge.todoist_api.TodoistAPI")
    def test_scans_todoist_when_enabled(self, mock_api_cls, vault_config):
        vault_config.is_module_enabled.side_effect = lambda name, profile=None: (
            name == "todoist_inbox"
        )
        mock_api = mock_api_cls.return_value
        mock_api.get_projects.return_value = [SimpleNamespace(id="inbox-1", is_inbox_project=True)]
        mock_api.get_tasks.return_value = [
            SimpleNamespace(id="1", content="Task", created_at=datetime.now(UTC).isoformat())
        ]

        items = scan_all(vault_config, profile="home")

        assert len(items) == 1
        assert items[0].label == "todoist_inbox"


class TestScanTodoistInbox:
    """Tests for scan_todoist_inbox."""

    def _config(self):
        config = Mock()
        config.get_todoist_token.return_value = "test-token"
        return config

    def test_no_token_returns_no_items(self):
        config = Mock()
        config.get_todoist_token.return_value = None
        assert scan_todoist_inbox(config) == []

    @patch("taskbridge.todoist_api.TodoistAPI")
    def test_no_inbox_project_returns_no_items(self, mock_api_cls):
        mock_api = mock_api_cls.return_value
        mock_api.get_projects.return_value = [SimpleNamespace(id="p1", is_inbox_project=False)]

        assert scan_todoist_inbox(self._config()) == []

    @patch("taskbridge.todoist_api.TodoistAPI")
    def test_empty_inbox_returns_no_items(self, mock_api_cls):
        mock_api = mock_api_cls.return_value
        mock_api.get_projects.return_value = [SimpleNamespace(id="inbox-1", is_inbox_project=True)]
        mock_api.get_tasks.return_value = []

        assert scan_todoist_inbox(self._config()) == []

    @patch("taskbridge.todoist_api.TodoistAPI")
    def test_stale_task_age_computed_from_created_at(self, mock_api_cls):
        mock_api = mock_api_cls.return_value
        mock_api.get_projects.return_value = [SimpleNamespace(id="inbox-1", is_inbox_project=True)]
        created = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        mock_api.get_tasks.return_value = [
            SimpleNamespace(id="1", content="Old task", created_at=created)
        ]

        items = scan_todoist_inbox(self._config())

        assert len(items) == 1
        assert items[0].label == "todoist_inbox"
        assert items[0].description == "Old task"
        assert items[0].age_days == pytest.approx(5, abs=0.01)

    @patch("taskbridge.todoist_api.TodoistAPI")
    def test_item_includes_showtask_uri(self, mock_api_cls):
        mock_api = mock_api_cls.return_value
        mock_api.get_projects.return_value = [SimpleNamespace(id="inbox-1", is_inbox_project=True)]
        mock_api.get_tasks.return_value = [
            SimpleNamespace(id="42", content="Task", created_at=datetime.now(UTC).isoformat())
        ]

        items = scan_todoist_inbox(self._config())

        assert items[0].uri == "https://todoist.com/showTask?id=42"

    @patch("taskbridge.todoist_api.TodoistAPI")
    def test_fetches_tasks_scoped_to_inbox_project_id(self, mock_api_cls):
        mock_api = mock_api_cls.return_value
        mock_api.get_projects.return_value = [SimpleNamespace(id="inbox-99", is_inbox_project=True)]
        mock_api.get_tasks.return_value = []

        scan_todoist_inbox(self._config())

        mock_api.get_tasks.assert_called_once_with(project_id="inbox-99")


class TestGroupByLabel:
    """Tests for group_by_label."""

    def test_groups_and_finds_oldest_per_label(self):
        items = [
            InboxItem(label="inbox", description="a.md", age_days=1.0, uri=""),
            InboxItem(label="inbox", description="b.md", age_days=5.0, uri=""),
            InboxItem(label="literature", description="c.md", age_days=2.0, uri=""),
        ]

        assert group_by_label(items) == [
            ("inbox", 2, 5.0),
            ("literature", 1, 2.0),
        ]

    def test_empty_items_returns_empty_list(self):
        assert group_by_label([]) == []


class TestInboxReportCommand:
    """CLI tests for `taskbridge inbox report`."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_no_modules_enabled_prints_clear_message(self, runner):
        with patch("taskbridge.main.config_manager") as cfg:
            cfg.is_module_enabled.return_value = False
            result = runner.invoke(app, ["inbox", "report"])

        assert result.exit_code == 0
        assert "No inbox sources configured or enabled" in result.stdout

    def test_enabled_but_no_items_reports_inbox_zero(self, runner):
        with patch("taskbridge.main.config_manager") as cfg:
            cfg.is_module_enabled.side_effect = lambda name, profile=None: name == "obsidian_inbox"
            cfg.get_inbox_folders.return_value = []
            result = runner.invoke(app, ["inbox", "report"])

        assert result.exit_code == 0
        assert "Inbox zero" in result.stdout

    def test_reports_grouped_summary_and_indexed_items(self, runner, tmp_path):
        inbox_dir = tmp_path / "00 Inbox"
        inbox_dir.mkdir()
        touch_with_age(inbox_dir / "Note.md", age_days=3)

        with patch("taskbridge.main.config_manager") as cfg:
            cfg.is_module_enabled.side_effect = lambda name, profile=None: name == "obsidian_inbox"
            cfg.get_inbox_folders.return_value = [{"label": "inbox", "path": "00 Inbox"}]
            cfg.get_obsidian_vault_path.return_value = str(tmp_path)
            cfg.generate_obsidian_file_url.return_value = "obsidian://open?vault=v&file=x"

            result = runner.invoke(app, ["inbox", "report"])

        assert result.exit_code == 0
        assert "inbox: 1 item(s), oldest 3.0d" in result.stdout
        assert "1. [inbox]" in result.stdout

    def test_profile_flag_is_forwarded(self, runner):
        with patch("taskbridge.main.config_manager") as cfg:
            cfg.is_module_enabled.return_value = False
            runner.invoke(app, ["inbox", "report", "--profile", "work"])

            cfg.is_module_enabled.assert_any_call("obsidian_inbox", profile="work")
            cfg.is_module_enabled.assert_any_call("todoist_inbox", profile="work")


class TestInboxOpenCommand:
    """CLI tests for `taskbridge inbox open`."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def _report_config(self, cfg, tmp_path, items_count=1):
        """Configure a mock so scan_all() returns items_count Obsidian items."""
        inbox_dir = tmp_path / "00 Inbox"
        inbox_dir.mkdir(exist_ok=True)
        for i in range(items_count):
            touch_with_age(inbox_dir / f"Note{i}.md", age_days=i + 1)

        cfg.is_module_enabled.side_effect = lambda name, profile=None: name == "obsidian_inbox"
        cfg.get_inbox_folders.return_value = [{"label": "inbox", "path": "00 Inbox"}]
        cfg.get_obsidian_vault_path.return_value = str(tmp_path)
        cfg.generate_obsidian_file_url.side_effect = lambda rel_path: (
            f"obsidian://open?vault=v&file={rel_path}"
        )

    def test_no_items_reports_clear_error(self, runner):
        with patch("taskbridge.main.config_manager") as cfg:
            cfg.is_module_enabled.return_value = False
            result = runner.invoke(app, ["inbox", "open", "1"])

        assert result.exit_code == 1
        assert "No inbox items currently reported" in result.stdout

    def test_index_out_of_range_reports_clear_error(self, runner, tmp_path):
        with patch("taskbridge.main.config_manager") as cfg:
            self._report_config(cfg, tmp_path, items_count=1)
            result = runner.invoke(app, ["inbox", "open", "5"])

        assert result.exit_code == 1
        assert "out of range" in result.stdout

    def test_zero_index_reports_clear_error(self, runner, tmp_path):
        with patch("taskbridge.main.config_manager") as cfg:
            self._report_config(cfg, tmp_path, items_count=1)
            result = runner.invoke(app, ["inbox", "open", "0"])

        assert result.exit_code == 1
        assert "out of range" in result.stdout

    @patch("taskbridge.main.subprocess.run")
    def test_valid_index_launches_uri_via_open(self, mock_run, runner, tmp_path):
        with patch("taskbridge.main.config_manager") as cfg:
            self._report_config(cfg, tmp_path, items_count=2)
            result = runner.invoke(app, ["inbox", "open", "1"])

        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            ["open", "obsidian://open?vault=v&file=00 Inbox/Note0.md"], check=True
        )

    @patch("taskbridge.main.subprocess.run")
    def test_shell_out_failure_reports_clear_error(self, mock_run, runner, tmp_path):
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, ["open"])

        with patch("taskbridge.main.config_manager") as cfg:
            self._report_config(cfg, tmp_path, items_count=1)
            result = runner.invoke(app, ["inbox", "open", "1"])

        assert result.exit_code == 1
        assert "Failed to open item" in result.stdout
