"""Unit tests for Config helpers added alongside the unified inbox report (ADR-002)."""

from taskbridge.config import Config


class TestObsidianFileUrl:
    """Tests for generate_obsidian_file_url and generate_obsidian_url."""

    def test_generate_obsidian_file_url_uses_vault_relative_path(self, tmp_path):
        config = Config(config_dir=tmp_path)
        config._config_data = {"obsidian_vault_name": "test-vault"}

        url = config.generate_obsidian_file_url("00 Inbox/Note.md")

        assert url == "obsidian://open?vault=test-vault&file=00%20Inbox/Note.md"

    def test_generate_obsidian_url_still_scopes_to_projects_folder(self, tmp_path):
        config = Config(config_dir=tmp_path)
        config._config_data = {"obsidian_vault_name": "test-vault"}

        url = config.generate_obsidian_url("MyProject", "Note.md")

        assert url == "obsidian://open?vault=test-vault&file=10%20Projects/MyProject/Note.md"


class TestInboxFolders:
    """Tests for get_inbox_folders."""

    def test_defaults_to_empty_list(self, tmp_path):
        config = Config(config_dir=tmp_path)
        config._config_data = {}

        assert config.get_inbox_folders() == []

    def test_returns_configured_folders(self, tmp_path):
        config = Config(config_dir=tmp_path)
        config._config_data = {"inbox_folders": [{"label": "inbox", "path": "00 Inbox"}]}

        assert config.get_inbox_folders() == [{"label": "inbox", "path": "00 Inbox"}]


def make_config(tmp_path, config_data):
    config = Config(config_dir=tmp_path)
    config._config_data = config_data
    return config


class TestModuleProfiles:
    """Tests for is_module_enabled (ADR-003)."""

    PROFILES = {
        "home": {"enabled_modules": ["obsidian_inbox", "todoist_inbox"]},
        "work": {"enabled_modules": ["obsidian_inbox", "todoist_inbox", "mail", "drafts"]},
    }

    def test_uses_default_profile_when_none_given(self, tmp_path):
        config = make_config(tmp_path, {"default_profile": "home", "profiles": self.PROFILES})

        assert config.is_module_enabled("obsidian_inbox") is True
        assert config.is_module_enabled("mail") is False

    def test_explicit_profile_overrides_default(self, tmp_path):
        config = make_config(tmp_path, {"default_profile": "home", "profiles": self.PROFILES})

        assert config.is_module_enabled("mail", profile="work") is True

    def test_module_not_listed_in_any_profile_is_disabled(self, tmp_path):
        config = make_config(tmp_path, {"default_profile": "work", "profiles": self.PROFILES})

        assert config.is_module_enabled("fantastical") is False

    def test_missing_profiles_block_disables_everything(self, tmp_path):
        config = make_config(tmp_path, {"default_profile": "home"})

        assert config.is_module_enabled("obsidian_inbox") is False

    def test_no_default_profile_and_no_explicit_profile_disables_everything(self, tmp_path):
        config = make_config(tmp_path, {"profiles": self.PROFILES})

        assert config.is_module_enabled("obsidian_inbox") is False

    def test_unknown_explicit_profile_disables_everything(self, tmp_path):
        config = make_config(tmp_path, {"profiles": self.PROFILES})

        assert config.is_module_enabled("obsidian_inbox", profile="vacation") is False


class TestCrossProcessConsistency:
    """Two Config instances on one file stand in for the CLI and the long-running web UI."""

    def test_reads_values_written_by_another_instance(self, tmp_path):
        server = Config(config_dir=tmp_path)
        cli = Config(config_dir=tmp_path)

        cli.set_template("ongoing", "email", "Email")

        assert "email" in server.get_templates("ongoing")

    def test_write_does_not_clobber_another_instances_changes(self, tmp_path):
        server = Config(config_dir=tmp_path)
        server.set("tag_colors", {})
        cli = Config(config_dir=tmp_path)

        cli.set_template("ongoing", "email", "Email")
        server.increment_template_usage("ongoing", "email")

        fresh = Config(config_dir=tmp_path)
        assert "email" in fresh.get_templates("ongoing")
        assert fresh.get_template_usage("ongoing") == {"email": 1}

    def test_picks_up_file_created_after_startup(self, tmp_path):
        server = Config(config_dir=tmp_path)
        (tmp_path / "config.yaml").write_text("obsidian_vault_name: v\n")

        assert server.get("obsidian_vault_name") == "v"
