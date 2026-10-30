"""Tests for linking backlog.md tasks to their parent Todoist task (ADR-004)."""

from unittest.mock import patch

import pytest
import requests
from typer.testing import CliRunner

from taskbridge import backlog
from taskbridge.main import app
from taskbridge.todoist_api import TodoistTask

URL = "https://app.todoist.com/app/task/6gRPQ6W25287Ccx7"

TASK = """---
id: TASK-09
title: Complete testing
status: To Do
labels:
  - testing
dependencies: []
{refs}priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Body with a --- rule and references: in prose.
<!-- SECTION:DESCRIPTION:END -->
"""


def write_task(repo, refs="", sub="tasks", name="task-09 - Complete-testing.md"):
    path = repo / "backlog" / sub / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TASK.format(refs=refs))
    return path


class TestTodoistTaskId:
    @pytest.mark.parametrize(
        "reference",
        [
            URL,
            URL + "/",
            "https://app.todoist.com/app/task/fix-the-bug-6gRPQ6W25287Ccx7",
            "  " + URL + "\n",
        ],
    )
    def test_reads_canonical_and_browser_forms(self, reference):
        assert backlog.todoist_task_id(reference) == "6gRPQ6W25287Ccx7"

    @pytest.mark.parametrize(
        "reference",
        [
            "https://app.todoist.com/app/project/work-6Jf8VQXxpwv56VQ7",
            "https://github.com/iross/taskbridge/pull/9",
            "http://app.todoist.com/app/task/6gRPQ6W25287Ccx7",
            "https://app.todoist.com/app/task/",
            "docs/notes.md",
        ],
    )
    def test_other_references_are_not_todoist_tasks(self, reference):
        assert backlog.todoist_task_id(reference) is None

    def test_url_round_trips(self):
        assert backlog.todoist_task_id(backlog.todoist_task_url("abc123")) == "abc123"


class TestFindTaskFile:
    @pytest.mark.parametrize("task_id", ["TASK-09", "task-9", "9", "09", " Task-9 "])
    def test_matches_any_spelling_of_the_id(self, tmp_path, task_id):
        path = write_task(tmp_path)
        assert backlog.find_task_file(tmp_path, task_id) == path

    def test_finds_completed_tasks(self, tmp_path):
        path = write_task(tmp_path, sub="completed")
        assert backlog.find_task_file(tmp_path, "TASK-9") == path

    def test_does_not_confuse_prefixes_or_subtasks(self, tmp_path):
        write_task(tmp_path, name="task-90 - Other.md")
        sub = write_task(tmp_path, name="task-9.01 - Subtask.md")
        with pytest.raises(backlog.BacklogError, match="TASK-9 not found"):
            backlog.find_task_file(tmp_path, "TASK-9")
        assert backlog.find_task_file(tmp_path, "task-9.1") == sub

    def test_missing_backlog_dir(self, tmp_path):
        with pytest.raises(backlog.BacklogError, match="No backlog/ directory"):
            backlog.find_task_file(tmp_path, "9")


class TestSetParentTask:
    def test_adds_references_when_task_has_none(self, tmp_path):
        path = write_task(tmp_path)

        assert backlog.set_parent_task(path, "abc") == [backlog.todoist_task_url("abc")]
        assert backlog.read_references(path) == [backlog.todoist_task_url("abc")]

    def test_replaces_existing_todoist_reference_and_keeps_others(self, tmp_path):
        refs = (
            "references:\n"
            "  - 'https://github.com/iross/taskbridge/pull/9'\n"
            "  - 'https://app.todoist.com/app/task/old-task-OLD1'\n"
            "  - 'docs/plan.md'\n"
        )
        path = write_task(tmp_path, refs=refs)

        backlog.set_parent_task(path, "NEW2")

        assert backlog.read_references(path) == [
            "https://github.com/iross/taskbridge/pull/9",
            "docs/plan.md",
            backlog.todoist_task_url("NEW2"),
        ]

    def test_replaces_inline_empty_list(self, tmp_path):
        path = write_task(tmp_path, refs="references: []\n")

        backlog.set_parent_task(path, "abc")

        assert backlog.read_references(path) == [backlog.todoist_task_url("abc")]
        assert path.read_text().count("references:") == 2  # frontmatter key + body prose

    def test_leaves_other_frontmatter_and_body_untouched(self, tmp_path):
        path = write_task(tmp_path)
        before = path.read_text()

        backlog.set_parent_task(path, "abc")

        after = path.read_text()
        removed = [line for line in before.splitlines() if line not in after.splitlines()]
        assert removed == []
        assert after.endswith(before.split("\n---\n", 1)[1])

    def test_quotes_in_other_references_survive(self, tmp_path):
        path = write_task(tmp_path, refs="references:\n  - 'it''s here'\n")

        backlog.set_parent_task(path, "abc")

        assert backlog.read_references(path)[0] == "it's here"

    def test_file_without_frontmatter_is_an_error(self, tmp_path):
        path = tmp_path / "task-1 - x.md"
        path.write_text("# no frontmatter\n")
        with pytest.raises(backlog.BacklogError, match="no frontmatter"):
            backlog.set_parent_task(path, "abc")


def todoist_task(task_id="PARENT1", content="Parent work"):
    return TodoistTask(id=task_id, content=content, description="", project_id="p1")


class TestBacklogLinkCommand:
    @pytest.fixture
    def api(self):
        with (
            patch("taskbridge.main.config_manager") as cfg,
            patch("taskbridge.main.TodoistAPI") as api_class,
        ):
            cfg.get_todoist_token.return_value = "token"
            api = api_class.return_value
            api.get_task.side_effect = lambda tid: todoist_task(tid) if tid == "PARENT1" else None
            yield api

    def link(self, tmp_path, *args):
        return CliRunner().invoke(app, ["backlog", "link", *args, "--repo", str(tmp_path)])

    def test_links_by_todoist_id(self, tmp_path, api):
        path = write_task(tmp_path)

        result = self.link(tmp_path, "9", "PARENT1")

        assert result.exit_code == 0, result.output
        assert "TASK-09 → Parent work" in result.output
        assert backlog.read_references(path) == [backlog.todoist_task_url("PARENT1")]

    def test_links_by_pasted_browser_url(self, tmp_path, api):
        path = write_task(tmp_path)

        result = self.link(tmp_path, "9", "https://app.todoist.com/app/task/parent-work-PARENT1")

        assert result.exit_code == 0, result.output
        assert backlog.read_references(path) == [backlog.todoist_task_url("PARENT1")]

    def test_picks_parent_with_fzf_when_omitted(self, tmp_path, api):
        path = write_task(tmp_path)
        api.get_tasks.return_value = [todoist_task(), todoist_task("DONE", "x")]
        api.get_tasks.return_value[1].is_completed = True

        with patch("taskbridge.main.pick_task_with_fzf", return_value="PARENT1") as pick:
            result = self.link(tmp_path, "9")

        assert result.exit_code == 0, result.output
        assert [t.id for t in pick.call_args.args[1]] == ["PARENT1"]
        assert backlog.read_references(path) == [backlog.todoist_task_url("PARENT1")]

    def test_cancelled_picker_changes_nothing(self, tmp_path, api):
        path = write_task(tmp_path)
        before = path.read_text()

        with patch("taskbridge.main.pick_task_with_fzf", return_value=None):
            result = self.link(tmp_path, "9")

        assert result.exit_code == 1
        assert path.read_text() == before

    def test_unknown_todoist_task_changes_nothing(self, tmp_path, api):
        path = write_task(tmp_path)
        before = path.read_text()

        result = self.link(tmp_path, "9", "NOPE")

        assert result.exit_code == 1
        assert "Todoist task NOPE not found" in result.output
        assert path.read_text() == before

    def test_unknown_backlog_task(self, tmp_path, api):
        write_task(tmp_path)

        result = self.link(tmp_path, "TASK-77", "PARENT1")

        assert result.exit_code == 1
        assert "Backlog task TASK-77 not found" in result.output
        api.get_task.assert_not_called()

    def test_todoist_unreachable_changes_nothing(self, tmp_path, api):
        path = write_task(tmp_path)
        before = path.read_text()
        api.get_task.side_effect = requests.exceptions.ConnectionError("offline")

        result = self.link(tmp_path, "9", "PARENT1")

        assert result.exit_code == 1
        assert "Could not look up Todoist task PARENT1: offline" in result.output
        assert path.read_text() == before
