"""Unit tests for todo.txt formatting."""

import re

from taskbridge.main import (
    _build_project_path,
    _extract_task_id,
    format_task_as_todo_txt,
    write_todo_txt,
)
from taskbridge.todoist_api import TodoistProject, TodoistTask


def make_task(**kwargs) -> TodoistTask:
    defaults = {
        "id": "1",
        "content": "Buy milk",
        "description": "",
        "project_id": "p1",
        "labels": [],
        "priority": 1,
        "due": None,
        "created_at": "2023-01-15T10:00:00Z",
        "is_completed": False,
        "completed_at": None,
    }
    defaults.update(kwargs)
    return TodoistTask(**defaults)


class TestFormatTaskAsTodoTxt:
    def test_active_no_priority(self):
        result = format_task_as_todo_txt(make_task(priority=1), "Groceries")
        assert result == "2023-01-15 Buy milk +Groceries id:1"

    def test_priority_a(self):
        result = format_task_as_todo_txt(make_task(priority=4), "Work")
        assert result.startswith("(A) 2023-01-15 Buy milk")

    def test_priority_b(self):
        result = format_task_as_todo_txt(make_task(priority=3), "")
        assert "(B)" in result

    def test_priority_c(self):
        result = format_task_as_todo_txt(make_task(priority=2), "")
        assert "(C)" in result

    def test_no_project_omits_plus_tag(self):
        result = format_task_as_todo_txt(make_task(), "")
        assert "+" not in result

    def test_project_spaces_replaced_with_underscores(self):
        result = format_task_as_todo_txt(make_task(), "My Project")
        assert "+My_Project" in result

    def test_labels_as_at_contexts(self):
        result = format_task_as_todo_txt(make_task(labels=["errands", "home"]), "")
        assert "@errands" in result
        assert "@home" in result

    def test_due_date_extension(self):
        result = format_task_as_todo_txt(make_task(due={"date": "2023-02-01"}), "")
        assert "due:2023-02-01" in result

    def test_due_date_datetime_truncated_to_date(self):
        result = format_task_as_todo_txt(make_task(due={"date": "2023-02-01T09:00:00"}), "")
        assert "due:2023-02-01" in result

    def test_no_due_date_omits_extension(self):
        result = format_task_as_todo_txt(make_task(due=None), "")
        assert "due:" not in result

    def test_creation_date_included(self):
        result = format_task_as_todo_txt(make_task(created_at="2023-01-15T10:00:00Z"), "")
        assert "2023-01-15" in result

    def test_no_created_at_omits_date(self):
        result = format_task_as_todo_txt(make_task(created_at=""), "")
        assert not re.search(r"\d{4}-\d{2}-\d{2}", result)

    def test_completed_task_x_prefix_with_completion_date(self):
        result = format_task_as_todo_txt(
            make_task(is_completed=True, completed_at="2023-01-20T12:00:00Z"), ""
        )
        assert result.startswith("x 2023-01-20")

    def test_completed_task_no_completed_at_uses_today(self):
        result = format_task_as_todo_txt(make_task(is_completed=True, completed_at=None), "")
        assert re.match(r"x \d{4}-\d{2}-\d{2}", result)

    def test_field_ordering_priority_date_content_project_label_due(self):
        task = make_task(priority=4, labels=["home"], due={"date": "2023-02-01"})
        result = format_task_as_todo_txt(task, "Work")
        parts = result.split()
        assert parts[0] == "(A)"
        assert parts[1] == "2023-01-15"
        assert parts[2] == "Buy"
        assert parts[3] == "milk"
        assert "+Work" in parts
        assert "@home" in parts
        assert "due:2023-02-01" in parts
        # Project and label come after content, due comes last
        content_idx = result.index("Buy milk")
        assert result.index("+Work") > content_idx
        assert result.index("due:2023-02-01") > result.index("+Work")

    def test_completed_task_preserves_priority(self):
        result = format_task_as_todo_txt(
            make_task(is_completed=True, completed_at="2023-01-20T00:00:00Z", priority=4), ""
        )
        assert result.startswith("x 2023-01-20 (A)")

    def test_client_emitted_as_key_value(self):
        result = format_task_as_todo_txt(make_task(), "Work", client="ACME")
        assert "client:ACME" in result

    def test_empty_client_omitted(self):
        result = format_task_as_todo_txt(make_task(), "Work", client="")
        assert "client:" not in result

    def test_client_comes_after_due_date(self):
        result = format_task_as_todo_txt(
            make_task(due={"date": "2023-02-01"}), "Work", client="ACME"
        )
        assert result.index("due:") < result.index("client:")

    def test_id_appended_at_end(self):
        result = format_task_as_todo_txt(make_task(id="task-42"), "Work")
        assert result.endswith("id:task-42")

    def test_id_after_client(self):
        result = format_task_as_todo_txt(make_task(id="task-42"), "Work", client="ACME")
        assert result.index("client:") < result.index("id:")

    def test_note_url_included(self):
        result = format_task_as_todo_txt(
            make_task(), "Work", note_url="obsidian://open?vault=v&file=f"
        )
        assert "note:obsidian://open?vault=v&file=f" in result

    def test_empty_note_url_omitted(self):
        result = format_task_as_todo_txt(make_task(), "Work", note_url="")
        assert "note:" not in result

    def test_note_url_before_id(self):
        result = format_task_as_todo_txt(make_task(), "Work", note_url="obsidian://x")
        assert result.index("note:") < result.index("id:")

    def test_nested_project_path_slash_preserved(self):
        result = format_task_as_todo_txt(make_task(), "CHTC/HTC26")
        assert "+CHTC/HTC26" in result

    def test_nested_project_spaces_replaced_within_segments(self):
        result = format_task_as_todo_txt(make_task(), "CHTC/HTC 26")
        assert "+CHTC/HTC_26" in result


def make_project(id: str, name: str, parent_id: str | None = None) -> TodoistProject:
    return TodoistProject(id=id, name=name, color="", parent_id=parent_id)


class TestBuildProjectPath:
    def test_flat_project(self):
        projects = {"p1": make_project("p1", "Work")}
        assert _build_project_path("p1", projects) == "Work"

    def test_two_level_hierarchy(self):
        projects = {
            "p1": make_project("p1", "CHTC"),
            "p2": make_project("p2", "HTC26", parent_id="p1"),
        }
        assert _build_project_path("p2", projects) == "CHTC/HTC26"

    def test_three_level_hierarchy(self):
        projects = {
            "p1": make_project("p1", "CHTC"),
            "p2": make_project("p2", "HTC26", parent_id="p1"),
            "p3": make_project("p3", "Agents", parent_id="p2"),
        }
        assert _build_project_path("p3", projects) == "CHTC/HTC26/Agents"

    def test_missing_project_returns_empty(self):
        assert _build_project_path("nonexistent", {}) == ""

    def test_missing_parent_stops_at_known_node(self):
        projects = {"p2": make_project("p2", "HTC26", parent_id="p1")}
        assert _build_project_path("p2", projects) == "HTC26"


class TestWriteTodoTxt:
    def test_preserves_existing_completed_lines(self, tmp_path, mocker):
        existing = "x 2023-01-10 2023-01-05 Old task +Work\n"
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text(existing)
        active = ["2023-01-15 Active task"]
        mocker.patch("taskbridge.main._fetch_todo_txt_lines", return_value=active)
        write_todo_txt(str(todo_file))
        content = todo_file.read_text()
        assert "x 2023-01-10 2023-01-05 Old task +Work" in content
        assert "2023-01-15 Active task" in content

    def test_extra_completed_lines_added(self, tmp_path, mocker):
        todo_file = tmp_path / "todo.txt"
        mocker.patch("taskbridge.main._fetch_todo_txt_lines", return_value=[])
        write_todo_txt(str(todo_file), extra_completed=["x 2023-01-20 Buy milk"])
        assert "x 2023-01-20 Buy milk" in todo_file.read_text()

    def test_orphaned_active_line_without_id_is_kept(self, tmp_path, mocker):
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("2023-01-05 Old active task\n")
        new_active = ["2023-01-15 New active task id:99"]
        mocker.patch("taskbridge.main._fetch_todo_txt_lines", return_value=new_active)
        write_todo_txt(str(todo_file))
        content = todo_file.read_text()
        assert "Old active task" in content
        assert "New active task" in content

    def test_orphaned_active_line_without_id_kept_silently(self, tmp_path, mocker, capsys):
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("2023-01-05 Orphaned task\n")
        mocker.patch("taskbridge.main._fetch_todo_txt_lines", return_value=[])
        write_todo_txt(str(todo_file))
        captured = capsys.readouterr()
        assert "Orphaned task" not in captured.out
        assert "Orphaned task" in todo_file.read_text()

    def test_active_line_with_id_not_in_todoist_marked_complete(self, tmp_path, mocker, capsys):
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("2023-01-05 GPU task +Work id:abc123\n")
        mocker.patch("taskbridge.main._fetch_todo_txt_lines", return_value=[])
        write_todo_txt(str(todo_file))
        content = todo_file.read_text()
        assert content.startswith("x ")
        assert "GPU task" in content
        captured = capsys.readouterr()
        assert "Marked complete" in captured.out

    def test_no_warning_when_active_line_matches_todoist(self, tmp_path, mocker, capsys):
        todo_file = tmp_path / "todo.txt"
        todo_file.write_text("2023-01-05 Buy milk\n")
        mocker.patch(
            "taskbridge.main._fetch_todo_txt_lines",
            return_value=["2023-01-15 Buy milk +Groceries id:1"],
        )
        write_todo_txt(str(todo_file))
        captured = capsys.readouterr()
        assert "not found in Todoist" not in captured.out


class TestExtractTaskId:
    def test_extracts_id(self):
        assert _extract_task_id("2023-01-15 Buy milk +Work id:abc123") == "abc123"

    def test_returns_none_when_absent(self):
        assert _extract_task_id("2023-01-15 Buy milk +Work") is None

    def test_works_on_completed_line(self):
        assert _extract_task_id("x 2023-01-20 Buy milk id:abc123") == "abc123"
