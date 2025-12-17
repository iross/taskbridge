"""Unit tests for Todoist API client."""

import pytest
from unittest.mock import Mock, patch
from taskbridge.todoist_api import TodoistAPI, TodoistProject, TodoistTask


class TestTodoistAPI:
    """Tests for TodoistAPI class."""

    def test_init_with_token(self, mock_config):
        """Test API initialization with token."""
        api = TodoistAPI(token="test-token")
        assert api.token == "test-token"

    def test_init_without_token_raises_error(self, mock_config):
        """Test API initialization without token raises ValueError."""
        mock_config.get_todoist_token.return_value = None
        with pytest.raises(ValueError, match="Todoist API token is required"):
            TodoistAPI()

    @patch('taskbridge.todoist_api.requests.Session')
    def test_validate_token_success(self, mock_session):
        """Test successful token validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.return_value.get.return_value = mock_response

        api = TodoistAPI(token="test-token")
        assert api.validate_token("test-token") is True

    @patch('taskbridge.todoist_api.requests.Session')
    def test_get_projects(self, mock_session, mock_todoist_api):
        """Test getting projects from API."""
        # This is a placeholder - you can expand with actual test logic
        pass

    def test_todoist_task_dataclass(self):
        """Test TodoistTask dataclass initialization."""
        task = TodoistTask(
            id="123",
            content="Test Task",
            description="Test description",
            project_id="proj-456"
        )
        assert task.id == "123"
        assert task.content == "Test Task"
        assert task.labels == []  # Default value from __post_init__
