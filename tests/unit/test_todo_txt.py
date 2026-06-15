"""Unit tests for todo.txt formatting."""

import re

from taskbridge.main import _build_project_path, format_task_as_todo_txt
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
        assert result == "2023-01-15 Buy milk +Groceries"

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
