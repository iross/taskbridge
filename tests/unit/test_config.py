"""Unit tests for Config helpers added alongside the unified inbox report (ADR-002)."""

from taskbridge.config import Config


class TestObsidianFileUrl:
    """Tests for generate_obsidian_file_url and generate_obsidian_url."""

    def test_generate_obsidian_file_url_uses_vault_relative_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Config, "__init__", lambda self: None)
        config = Config()
        config._config_data = {"obsidian_vault_name": "test-vault"}

        url = config.generate_obsidian_file_url("00 Inbox/Note.md")

        assert url == "obsidian://open?vault=test-vault&file=00%20Inbox/Note.md"

    def test_generate_obsidian_url_still_scopes_to_projects_folder(self, monkeypatch):
        monkeypatch.setattr(Config, "__init__", lambda self: None)
        config = Config()
        config._config_data = {"obsidian_vault_name": "test-vault"}

        url = config.generate_obsidian_url("MyProject", "Note.md")

        assert url == "obsidian://open?vault=test-vault&file=10%20Projects/MyProject/Note.md"


class TestInboxFolders:
    """Tests for get_inbox_folders."""

    def test_defaults_to_empty_list(self, monkeypatch):
        monkeypatch.setattr(Config, "__init__", lambda self: None)
        config = Config()
        config._config_data = {}

        assert config.get_inbox_folders() == []

    def test_returns_configured_folders(self, monkeypatch):
        monkeypatch.setattr(Config, "__init__", lambda self: None)
        config = Config()
        config._config_data = {"inbox_folders": [{"label": "inbox", "path": "00 Inbox"}]}

        assert config.get_inbox_folders() == [{"label": "inbox", "path": "00 Inbox"}]
