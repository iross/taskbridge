"""Tests for linking backlog.md tasks to their parent Todoist task (ADR-004)."""

from unittest.mock import Mock, patch

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


def write_numbered(repo, number, title, refs=""):
    path = write_task(repo, refs=refs, name=f"task-{number} - {title}.md")
    path.write_text(
        path.read_text().replace("TASK-09", f"TASK-{number}").replace("Complete testing", title)
    )
    return path


class FakeFzf:
    """Stands in for fzf at the subprocess boundary; picks lines by a substring."""

    def __init__(self, picks):
        self.picks = list(picks)
        self.calls = []

    def __call__(self, cmd, **kwargs):
        if cmd[0] == "which":
            return Mock(returncode=0)
        lines = kwargs["input"].split("\n")
        self.calls.append((cmd, lines))
        pick = self.picks.pop(0)
        if pick is None:
            return Mock(returncode=130, stdout="")
        chosen = [line for line in lines if any(p in line for p in pick)]
        return Mock(returncode=0, stdout="\n".join(chosen) + "\n")


class TestBacklogLinkCommand:
    @pytest.fixture
    def api(self):
        with (
            patch("taskbridge.main.config_manager") as cfg,
            patch("taskbridge.main.TodoistAPI") as api_class,
            patch("taskbridge.main.db") as db,
        ):
            cfg.get_todoist_token.return_value = "token"
            api = api_class.return_value
            api.get_task.side_effect = lambda tid: (
                todoist_task(tid) if tid in ("PARENT1", "OTHER") else None
            )
            api.get_tasks.return_value = [todoist_task("OTHER", "Other work"), todoist_task()]
            api.get_project.return_value = None
            db.get_active_tracking.return_value = None
            api.db = db
            yield api

    def link(self, tmp_path, *args):
        return CliRunner().invoke(app, ["backlog", "link", *args, "--repo", str(tmp_path)])

    def fzf(self, *picks):
        fake = FakeFzf(picks)
        return fake, patch("taskbridge.main.subprocess.run", fake)

    def test_links_one_task_and_says_what_it_linked(self, tmp_path, api):
        path = write_task(tmp_path)

        result = self.link(tmp_path, "9", "--to", "PARENT1")

        assert result.exit_code == 0, result.output
        assert "🔗 TASK-09  Complete testing" in result.output
        assert "→ Parent work" in result.output
        assert backlog.read_references(path) == [backlog.todoist_task_url("PARENT1")]

    def test_links_several_tasks_to_a_pasted_url(self, tmp_path, api):
        a = write_numbered(tmp_path, 10, "Alpha")
        b = write_numbered(tmp_path, 11, "Beta")
        url = "https://app.todoist.com/app/task/parent-work-PARENT1"

        result = self.link(tmp_path, "10", "TASK-11", "task-10", "--to", url)

        assert result.exit_code == 0, result.output
        assert result.output.count("🔗") == 2
        for path in (a, b):
            assert backlog.read_references(path) == [backlog.todoist_task_url("PARENT1")]

    def test_unknown_task_among_several_changes_nothing(self, tmp_path, api):
        a = write_numbered(tmp_path, 10, "Alpha")
        before = a.read_text()

        result = self.link(tmp_path, "10", "TASK-77", "--to", "PARENT1")

        assert result.exit_code == 1
        assert "Backlog task TASK-77 not found" in result.output
        assert a.read_text() == before
        api.get_task.assert_not_called()

    def test_parent_picker_names_the_tasks_and_lists_current_task_first(self, tmp_path, api):
        write_numbered(tmp_path, 10, "Alpha")
        write_numbered(tmp_path, 11, "Beta")
        api.db.get_active_tracking.return_value = Mock(todoist_task_id="PARENT1")
        fake, fzf = self.fzf(["PARENT1 |"])

        with fzf:
            result = self.link(tmp_path, "10", "11")

        assert result.exit_code == 0, result.output
        cmd, lines = fake.calls[0]
        header = cmd[cmd.index("--header") + 1]
        assert header == "Parent for:\n  TASK-10  Alpha\n  TASK-11  Beta"
        assert lines[0].startswith("PARENT1 | ") and lines[1].startswith("OTHER | ")

    def test_backlog_picker_multi_selects_newest_first(self, tmp_path, api):
        a = write_numbered(tmp_path, 10, "Alpha")
        write_numbered(
            tmp_path, 11, "Beta", refs=f"references:\n  - '{backlog.todoist_task_url('X')}'\n"
        )
        c = write_numbered(tmp_path, 12, "Gamma")
        fake, fzf = self.fzf(["Alpha", "Gamma"])

        with fzf:
            result = self.link(tmp_path, "--to", "OTHER")

        assert result.exit_code == 0, result.output
        cmd, lines = fake.calls[0]
        assert "--multi" in cmd
        assert cmd[cmd.index("--preview") + 1] == "cat {2}"
        assert [line.split()[0] for line in lines] == ["TASK-12", "TASK-11", "TASK-10"]
        assert lines[1].split("\t")[0] == f"{'TASK-11':<9} {'To Do':<12} 🔗 Beta"
        assert lines[0].split("\t")[1] == str(c)
        for path in (a, c):
            assert backlog.read_references(path) == [backlog.todoist_task_url("OTHER")]
        assert "Beta" not in result.output

    @pytest.mark.parametrize("picks", [[None], [["Alpha"], None]])
    def test_cancelled_picker_changes_nothing(self, tmp_path, api, picks):
        path = write_numbered(tmp_path, 10, "Alpha")
        before = path.read_text()
        _, fzf = self.fzf(*picks)

        with fzf:
            result = self.link(tmp_path)

        assert result.exit_code == 1
        assert path.read_text() == before

    def test_unknown_todoist_task_changes_nothing(self, tmp_path, api):
        path = write_task(tmp_path)
        before = path.read_text()

        result = self.link(tmp_path, "9", "--to", "NOPE")

        assert result.exit_code == 1
        assert "Todoist task NOPE not found" in result.output
        assert path.read_text() == before

    def test_todoist_unreachable_changes_nothing(self, tmp_path, api):
        path = write_task(tmp_path)
        before = path.read_text()
        api.get_task.side_effect = requests.exceptions.ConnectionError("offline")

        result = self.link(tmp_path, "9", "--to", "PARENT1")

        assert result.exit_code == 1
        assert "Could not look up Todoist task PARENT1: offline" in result.output
        assert path.read_text() == before
