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


def make_config(monkeypatch, config_data):
    monkeypatch.setattr(Config, "__init__", lambda self: None)
    config = Config()
    config._config_data = config_data
    return config


class TestModuleProfiles:
    """Tests for is_module_enabled (ADR-003)."""

    PROFILES = {
        "home": {"enabled_modules": ["obsidian_inbox", "todoist_inbox"]},
        "work": {"enabled_modules": ["obsidian_inbox", "todoist_inbox", "mail", "drafts"]},
    }

    def test_uses_default_profile_when_none_given(self, monkeypatch):
        config = make_config(monkeypatch, {"default_profile": "home", "profiles": self.PROFILES})

        assert config.is_module_enabled("obsidian_inbox") is True
        assert config.is_module_enabled("mail") is False

    def test_explicit_profile_overrides_default(self, monkeypatch):
        config = make_config(monkeypatch, {"default_profile": "home", "profiles": self.PROFILES})

        assert config.is_module_enabled("mail", profile="work") is True

    def test_module_not_listed_in_any_profile_is_disabled(self, monkeypatch):
        config = make_config(monkeypatch, {"default_profile": "work", "profiles": self.PROFILES})

        assert config.is_module_enabled("fantastical") is False

    def test_missing_profiles_block_disables_everything(self, monkeypatch):
        config = make_config(monkeypatch, {"default_profile": "home"})

        assert config.is_module_enabled("obsidian_inbox") is False

    def test_no_default_profile_and_no_explicit_profile_disables_everything(self, monkeypatch):
        config = make_config(monkeypatch, {"profiles": self.PROFILES})

        assert config.is_module_enabled("obsidian_inbox") is False

    def test_unknown_explicit_profile_disables_everything(self, monkeypatch):
        config = make_config(monkeypatch, {"profiles": self.PROFILES})

        assert config.is_module_enabled("obsidian_inbox", profile="vacation") is False
