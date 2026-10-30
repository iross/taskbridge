"""Unit tests for Todoist API client."""

from unittest.mock import Mock, patch

import pytest
import requests

from taskbridge.todoist_api import TodoistAPI, TodoistTask


class TestTodoistAPI:
    """Tests for TodoistAPI class."""

    def test_init_with_token(self, mock_config):
        """Test API initialization with token."""
        api = TodoistAPI(token="test-token")
        assert api.token == "test-token"

    @patch("taskbridge.todoist_api.config_manager")
    def test_init_without_token_raises_error(self, mock_config_manager):
        """Test API initialization without token raises ValueError."""
        mock_config_manager.get_todoist_token.return_value = None
        with pytest.raises(ValueError, match="Todoist API token is required"):
            TodoistAPI()

    @patch("taskbridge.todoist_api.requests.get")
    def test_validate_token_success(self, mock_get):
        """Test successful token validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        api = TodoistAPI(token="test-token")
        assert api.validate_token("test-token") is True

    @patch("taskbridge.todoist_api.requests.Session")
    def test_get_projects(self, mock_session, mock_todoist_api):
        """Test getting projects from API."""
        # This is a placeholder - you can expand with actual test logic
        pass

    def test_todoist_task_dataclass(self):
        """Test TodoistTask dataclass initialization."""
        task = TodoistTask(
            id="123", content="Test Task", description="Test description", project_id="proj-456"
        )
        assert task.id == "123"
        assert task.content == "Test Task"
        assert task.labels == []  # Default value from __post_init__


def http_response(status, body=b"{}"):
    response = requests.Response()
    response.status_code = status
    response._content = body
    response.url = "https://api.todoist.com/api/v1/tasks/x"
    return response


class TestGetTask:
    """get_task returns None for IDs that cannot name a task, and raises otherwise."""

    @pytest.fixture
    def api(self):
        return TodoistAPI(token="test-token")

    def test_returns_task(self, api):
        body = b'{"id": "6gRP", "content": "Parent", "project_id": "p1"}'
        api.session.request = Mock(return_value=http_response(200, body))

        assert api.get_task("6gRP").content == "Parent"

    @pytest.mark.parametrize("status", [400, 404])
    def test_unknown_or_malformed_id_is_none(self, api, status):
        api.session.request = Mock(return_value=http_response(status))

        assert api.get_task("NOPE123") is None

    def test_other_errors_raise(self, api):
        api.session.request = Mock(return_value=http_response(500))

        with pytest.raises(requests.exceptions.HTTPError):
            api.get_task("6gRP")
