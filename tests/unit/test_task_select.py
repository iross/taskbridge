"""Tests for Todoist priority coloring in `task select`."""

from unittest.mock import Mock, patch

import typer
from typer.testing import CliRunner

from taskbridge.main import app, format_task_priority
from taskbridge.todoist_api import TodoistTask


def make_task(task_id="1", content="Task", priority=1):
    return TodoistTask(
        id=task_id,
        content=content,
        description="",
        project_id="p1",
        priority=priority,
    )


class TestFormatTaskPriority:
    def test_priority_one_is_unstyled(self):
        assert format_task_priority("Task", 1) == "Task"

    def test_priority_four_is_colored_red(self):
        styled = format_task_priority("Task", 4)
        assert typer.unstyle(styled) == "Task"
        assert "\x1b[38;2;235;87;87m" in styled

    def test_each_priority_gets_a_distinct_color(self):
        colored = {p: format_task_priority("Task", p) for p in (2, 3, 4)}
        assert len({colored[2], colored[3], colored[4]}) == 3


class TestTaskSelectCommand:
    @patch("taskbridge.main.subprocess.run")
    @patch("taskbridge.main.TodoistAPI")
    @patch("taskbridge.main.config_manager")
    def test_fzf_invoked_with_ansi_flag(self, mock_cfg, mock_api_class, mock_run):
        mock_cfg.get_todoist_token.return_value = "token"
        mock_api = mock_api_class.return_value
        mock_api.get_tasks.return_value = [make_task(priority=4)]

        which_result = Mock(returncode=0)
        fzf_result = Mock(returncode=0, stdout="1 | Task\n")
        mock_run.side_effect = [which_result, fzf_result]

        result = CliRunner().invoke(app, ["task", "select"])

        assert result.exit_code == 0
        fzf_call_args = mock_run.call_args_list[1].args[0]
        assert "--ansi" in fzf_call_args

    @patch("taskbridge.main.subprocess.run")
    @patch("taskbridge.main.TodoistAPI")
    @patch("taskbridge.main.config_manager")
    def test_high_priority_task_line_is_colored(self, mock_cfg, mock_api_class, mock_run):
        mock_cfg.get_todoist_token.return_value = "token"
        mock_api = mock_api_class.return_value
        mock_api.get_tasks.return_value = [make_task(task_id="42", content="Urgent", priority=4)]

        which_result = Mock(returncode=0)
        fzf_result = Mock(returncode=0, stdout="42 | Urgent\n")
        mock_run.side_effect = [which_result, fzf_result]

        CliRunner().invoke(app, ["task", "select"])

        fzf_input = mock_run.call_args_list[1].kwargs["input"]
        assert "\x1b[38;2;235;87;87m" in fzf_input

    @patch("taskbridge.main.subprocess.run")
    @patch("taskbridge.main.TodoistAPI")
    @patch("taskbridge.main.config_manager")
    def test_normal_priority_task_line_is_uncolored(self, mock_cfg, mock_api_class, mock_run):
        mock_cfg.get_todoist_token.return_value = "token"
        mock_api = mock_api_class.return_value
        mock_api.get_tasks.return_value = [make_task(task_id="1", content="Plain", priority=1)]

        which_result = Mock(returncode=0)
        fzf_result = Mock(returncode=0, stdout="1 | Plain\n")
        mock_run.side_effect = [which_result, fzf_result]

        CliRunner().invoke(app, ["task", "select"])

        fzf_input = mock_run.call_args_list[1].kwargs["input"]
        assert "1 | Plain" in fzf_input
        assert "\x1b[" not in fzf_input

    @patch("taskbridge.main.subprocess.run")
    @patch("taskbridge.main.TodoistAPI")
    @patch("taskbridge.main.config_manager")
    def test_selected_task_id_extracted_despite_color_codes(
        self, mock_cfg, mock_api_class, mock_run
    ):
        mock_cfg.get_todoist_token.return_value = "token"
        mock_api = mock_api_class.return_value
        mock_api.get_tasks.return_value = [make_task(task_id="42", content="Urgent", priority=4)]

        which_result = Mock(returncode=0)
        colored_line = f"42 | {format_task_priority('Urgent', 4)}"
        fzf_result = Mock(returncode=0, stdout=colored_line + "\n")
        mock_run.side_effect = [which_result, fzf_result]

        result = CliRunner().invoke(app, ["task", "select"])

        assert result.exit_code == 0
        assert result.stdout.strip() == "42"
