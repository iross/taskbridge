"""Tests for tag pill colors and the config tag-color command."""

from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from taskbridge.main import app


@pytest.fixture
def runner():
    return CliRunner()


class TestTagColor:
    def test_auto_color_is_stable_and_from_palette(self):
        from taskbridge.main import TAG_PALETTE, tag_color

        with patch("taskbridge.main.config_manager") as cfg:
            cfg.get_tag_colors.return_value = {}

            assert tag_color("meeting") == tag_color("meeting")
            assert tag_color("meeting") in TAG_PALETTE

    def test_override_honored_case_insensitively(self):
        from taskbridge.main import tag_color

        with patch("taskbridge.main.config_manager") as cfg:
            cfg.get_tag_colors.return_value = {"meeting": "#123abc"}

            assert tag_color("Meeting") == "#123abc"

    def test_invalid_override_raises_with_fix_hint(self):
        from taskbridge.main import tag_color

        with patch("taskbridge.main.config_manager") as cfg:
            cfg.get_tag_colors.return_value = {"meeting": "blue"}

            with pytest.raises(ValueError, match="tag-color"):
                tag_color("meeting")


class TestFormatTagPill:
    def test_pill_text_is_padded_tag(self):
        from taskbridge.main import format_tag_pill

        with patch("taskbridge.main.config_manager") as cfg:
            cfg.get_tag_colors.return_value = {}

            assert typer.unstyle(format_tag_pill("meeting")) == " meeting "

    def test_pill_has_truecolor_background(self):
        from taskbridge.main import format_tag_pill

        with patch("taskbridge.main.config_manager") as cfg:
            cfg.get_tag_colors.return_value = {}

            assert "\x1b[48;2;" in format_tag_pill("meeting")

    def test_foreground_contrasts_with_background(self):
        from taskbridge.main import format_tag_pill

        with patch("taskbridge.main.config_manager") as cfg:
            cfg.get_tag_colors.return_value = {"light": "#ffffff", "dark": "#000000"}

            assert "\x1b[38;2;0;0;0m" in format_tag_pill("light")  # black text on white
            assert "\x1b[38;2;255;255;255m" in format_tag_pill("dark")  # white text on black

    def test_pills_joined_with_spaces(self):
        from taskbridge.main import format_tag_pills

        with patch("taskbridge.main.config_manager") as cfg:
            cfg.get_tag_colors.return_value = {}

            assert typer.unstyle(format_tag_pills(["a", "b"])) == " a   b "


class TestConfigTagColorCommand:
    @patch("taskbridge.main.config_manager")
    def test_set_valid_color(self, mock_cfg, runner):
        mock_cfg.get_tag_colors.return_value = {}

        result = runner.invoke(app, ["config", "tag-color", "meeting", "#5c7cfa"])

        assert result.exit_code == 0
        mock_cfg.set_tag_color.assert_called_once_with("meeting", "#5c7cfa")

    @patch("taskbridge.main.config_manager")
    def test_set_rejects_invalid_color(self, mock_cfg, runner):
        result = runner.invoke(app, ["config", "tag-color", "meeting", "blue"])

        assert result.exit_code == 1
        assert "Invalid color" in result.output
        mock_cfg.set_tag_color.assert_not_called()

    @patch("taskbridge.main.config_manager")
    def test_list_overrides(self, mock_cfg, runner):
        mock_cfg.get_tag_colors.return_value = {"meeting": "#5c7cfa"}

        result = runner.invoke(app, ["config", "tag-color"])

        assert result.exit_code == 0
        assert "meeting" in result.output
        assert "#5c7cfa" in result.output

    @patch("taskbridge.main.config_manager")
    def test_list_when_empty(self, mock_cfg, runner):
        mock_cfg.get_tag_colors.return_value = {}

        result = runner.invoke(app, ["config", "tag-color"])

        assert result.exit_code == 0
        assert "auto-assigned" in result.output

    @patch("taskbridge.main.config_manager")
    def test_remove_existing_override(self, mock_cfg, runner):
        mock_cfg.remove_tag_color.return_value = True

        result = runner.invoke(app, ["config", "tag-color", "meeting", "--remove"])

        assert result.exit_code == 0
        mock_cfg.remove_tag_color.assert_called_once_with("meeting")

    @patch("taskbridge.main.config_manager")
    def test_remove_missing_override_fails(self, mock_cfg, runner):
        mock_cfg.remove_tag_color.return_value = False

        result = runner.invoke(app, ["config", "tag-color", "missing", "--remove"])

        assert result.exit_code == 1


class TestConfigTagColorStorage:
    def test_set_get_remove_roundtrip(self, tmp_path, monkeypatch):
        from pathlib import Path

        from taskbridge.config import Config

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cfg = Config()

        cfg.set_tag_color("Meeting", "#123abc")
        assert cfg.get_tag_colors() == {"meeting": "#123abc"}

        assert cfg.remove_tag_color("MEETING") is True
        assert cfg.get_tag_colors() == {}
        assert cfg.remove_tag_color("meeting") is False
