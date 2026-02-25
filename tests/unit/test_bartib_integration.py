"""Tests for bartib time tracking integration."""

from unittest.mock import Mock, patch

import pytest

from taskbridge.bartib_integration import BartibIntegration


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for bartib CLI calls."""
    with patch("taskbridge.bartib_integration.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def bartib(mock_subprocess):
    """Create BartibIntegration instance with mocked subprocess."""
    mock_subprocess.return_value = Mock(returncode=0, stdout="bartib 1.1.0\n", stderr="")
    return BartibIntegration()


class TestBartibIntegrationInit:
    """Test BartibIntegration initialization."""

    def test_init_verifies_binary(self, mock_subprocess):
        """Test that init verifies bartib binary exists."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="bartib 1.1.0\n", stderr="")

        BartibIntegration()

        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert args[0] == "bartib"
        assert "--version" in args

    def test_init_raises_on_missing_binary(self, mock_subprocess):
        """Test that init raises error if bartib is not found."""
        mock_subprocess.side_effect = FileNotFoundError("bartib not found")

        with pytest.raises(RuntimeError, match="bartib not found"):
            BartibIntegration()

    def test_init_raises_on_non_zero_exit(self, mock_subprocess):
        """Test that init raises error if bartib version fails."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="error")

        with pytest.raises(RuntimeError, match="not working"):
            BartibIntegration()


class TestStartTracking:
    """Test start_tracking method."""

    def test_start_tracking_basic(self, bartib, mock_subprocess):
        """Test starting tracking with description and project."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.start_tracking(description="Working on tests", project="taskbridge")

        args = mock_subprocess.call_args[0][0]
        assert args[0] == "bartib"
        assert "start" in args
        assert "-d" in args
        assert "Working on tests" in args
        assert "-p" in args
        assert "taskbridge" in args

    def test_start_tracking_with_time(self, bartib, mock_subprocess):
        """Test starting tracking with custom start time."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.start_tracking(description="Test", project="proj", start_time="09:30")

        args = mock_subprocess.call_args[0][0]
        assert "-t" in args
        assert "09:30" in args

    def test_start_tracking_raises_on_error(self, bartib, mock_subprocess):
        """Test that start raises RuntimeError on bartib failure."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="no activity running")

        with pytest.raises(RuntimeError, match="bartib error"):
            bartib.start_tracking(description="Test", project="proj")


class TestStopTracking:
    """Test stop_tracking method."""

    def test_stop_tracking_basic(self, bartib, mock_subprocess):
        """Test stopping tracking."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.stop_tracking()

        args = mock_subprocess.call_args[0][0]
        assert "stop" in args

    def test_stop_tracking_with_time(self, bartib, mock_subprocess):
        """Test stopping tracking at a specific time."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.stop_tracking(stop_time="17:00")

        args = mock_subprocess.call_args[0][0]
        assert "-t" in args
        assert "17:00" in args


class TestListActivities:
    """Test list_activities method."""

    def test_list_activities_today(self, bartib, mock_subprocess):
        """Test listing today's activities."""
        sample_output = "2026-02-25\n  09:00 - 10:00 (1:00 h) [taskbridge] Testing\n"
        mock_subprocess.return_value = Mock(returncode=0, stdout=sample_output, stderr="")

        result = bartib.list_activities(today=True)

        args = mock_subprocess.call_args[0][0]
        assert "list" in args
        assert "--today" in args
        assert result == sample_output

    def test_list_activities_current_week(self, bartib, mock_subprocess):
        """Test listing current week's activities."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.list_activities(current_week=True)

        args = mock_subprocess.call_args[0][0]
        assert "--current_week" in args

    def test_list_activities_with_project_filter(self, bartib, mock_subprocess):
        """Test listing activities filtered by project."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.list_activities(project="taskbridge", today=True)

        args = mock_subprocess.call_args[0][0]
        assert "-p" in args
        assert "taskbridge" in args

    def test_list_activities_from_date(self, bartib, mock_subprocess):
        """Test listing activities from a specific date."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.list_activities(from_date="2026-02-18", to_date="2026-02-25")

        args = mock_subprocess.call_args[0][0]
        assert "--from" in args
        assert "2026-02-18" in args
        assert "--to" in args
        assert "2026-02-25" in args

    def test_list_activities_with_number(self, bartib, mock_subprocess):
        """Test listing activities with a count limit."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.list_activities(number=10)

        args = mock_subprocess.call_args[0][0]
        assert "-n" in args
        assert "10" in args


class TestGetReport:
    """Test get_report method."""

    def test_get_report_today(self, bartib, mock_subprocess):
        """Test getting today's report."""
        sample_report = "taskbridge  1:00 h\n"
        mock_subprocess.return_value = Mock(returncode=0, stdout=sample_report, stderr="")

        result = bartib.get_report(today=True)

        args = mock_subprocess.call_args[0][0]
        assert "report" in args
        assert "--today" in args
        assert result == sample_report

    def test_get_report_current_week(self, bartib, mock_subprocess):
        """Test getting current week report."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.get_report(current_week=True)

        args = mock_subprocess.call_args[0][0]
        assert "--current_week" in args

    def test_get_report_last_week(self, bartib, mock_subprocess):
        """Test getting last week report."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.get_report(last_week=True)

        args = mock_subprocess.call_args[0][0]
        assert "--last_week" in args

    def test_get_report_with_project(self, bartib, mock_subprocess):
        """Test getting report filtered by project."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        bartib.get_report(project="client/project", today=True)

        args = mock_subprocess.call_args[0][0]
        assert "-p" in args
        assert "client/project" in args


class TestGetCurrent:
    """Test get_current method."""

    def test_get_current_with_active(self, bartib, mock_subprocess):
        """Test getting currently running activity."""
        sample_output = "  09:00 - ongoing [taskbridge] Working on feature\n"
        mock_subprocess.return_value = Mock(returncode=0, stdout=sample_output, stderr="")

        result = bartib.get_current()

        args = mock_subprocess.call_args[0][0]
        assert "current" in args
        assert result == sample_output

    def test_get_current_empty(self, bartib, mock_subprocess):
        """Test get_current when nothing is running."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        result = bartib.get_current()

        assert result == ""
