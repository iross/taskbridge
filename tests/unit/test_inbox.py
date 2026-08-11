"""Unit tests for cross-tool inbox scanning (ADR-002)."""

import os
import time
from unittest.mock import Mock

import pytest

from taskbridge.inbox import scan_obsidian_folders


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
