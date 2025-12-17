"""Global pytest fixtures for taskbridge tests."""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path


@pytest.fixture
def mock_config():
    """Mock configuration manager."""
    mock = Mock()
    mock.get.return_value = None
    mock.get_linear_token.return_value = "test-linear-token"
    mock.get_toggl_token.return_value = "test-toggl-token"
    mock.get_todoist_token.return_value = "test-todoist-token"
    mock.get_obsidian_vault_path.return_value = "/tmp/test-vault"
    mock.get_obsidian_vault_name.return_value = "test-vault"
    mock.get_todoist_sync_label.return_value = "@obsidian"
    mock.get_todoist_project_mappings.return_value = {}
    return mock


@pytest.fixture
def mock_db():
    """Mock database instance."""
    mock = Mock()
    mock.create_project.return_value = 1
    mock.get_project.return_value = None
    mock.get_all_projects.return_value = []
    mock.create_todoist_note_mapping.return_value = 1
    mock.get_todoist_note_by_task_id.return_value = None
    mock.get_all_todoist_mappings.return_value = []
    return mock


@pytest.fixture
def mock_linear_api():
    """Mock Linear API client."""
    mock = Mock()
    mock.get_projects.return_value = []
    mock.get_project.return_value = None
    mock.get_issues.return_value = []
    return mock


@pytest.fixture
def mock_toggl_api():
    """Mock Toggl API client."""
    mock = Mock()
    mock.get_clients.return_value = []
    mock.get_projects.return_value = []
    mock.get_current_time_entry.return_value = None
    return mock


@pytest.fixture
def mock_todoist_api():
    """Mock Todoist API client."""
    mock = Mock()
    mock.get_projects.return_value = []
    mock.get_project.return_value = None
    mock.get_tasks.return_value = []
    mock.get_task.return_value = None
    mock.create_project.return_value = Mock(id="proj-123", name="Test Project", url="https://todoist.com/app/project/proj-123")
    mock.create_comment.return_value = True
    return mock


@pytest.fixture
def mock_requests_session():
    """Mock requests session for API calls."""
    mock = MagicMock()
    mock.request.return_value.status_code = 200
    mock.request.return_value.json.return_value = {}
    return mock


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary Obsidian vault for testing."""
    vault_path = tmp_path / "test-vault"
    vault_path.mkdir()
    (vault_path / "10 Projects").mkdir(parents=True)
    return vault_path


@pytest.fixture
def sample_todoist_task():
    """Sample Todoist task data."""
    from taskbridge.todoist_api import TodoistTask
    return TodoistTask(
        id="task-123",
        content="Test Task",
        description="Test description",
        project_id="proj-456",
        labels=["@obsidian", "important"],
        priority=1,
        url="https://todoist.com/app/task/task-123"
    )


@pytest.fixture
def sample_todoist_project():
    """Sample Todoist project data."""
    from taskbridge.todoist_api import TodoistProject
    return TodoistProject(
        id="proj-123",
        name="Test Project",
        color="blue",
        url="https://todoist.com/app/project/proj-123"
    )


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset any global state between tests."""
    yield
    # Add any cleanup needed here
