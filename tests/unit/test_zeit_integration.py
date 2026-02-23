"""Tests for zeit time tracking integration."""

import json
from unittest.mock import Mock, patch

import pytest

from taskbridge.zeit_integration import TimeBlock, ZeitIntegration, ZeitProject


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for zeit CLI calls."""
    with patch("taskbridge.zeit_integration.subprocess.run") as mock_run:
        # Default: successful command with empty JSON array
        mock_run.return_value = Mock(returncode=0, stdout="[]", stderr="")
        yield mock_run


@pytest.fixture
def zeit_integration(mock_subprocess):
    """Create ZeitIntegration instance with mocked subprocess."""
    return ZeitIntegration()


class TestZeitIntegrationInit:
    """Test ZeitIntegration initialization."""

    def test_init_verifies_zeit_binary(self, mock_subprocess):
        """Test that init verifies zeit binary exists."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="v1.0.0\n", stderr="")

        ZeitIntegration()

        # Should call zeit version to verify it's installed
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert args[0] == "zeit"
        assert "version" in args

    def test_init_raises_on_missing_binary(self, mock_subprocess):
        """Test that init raises error if zeit is not found."""
        mock_subprocess.side_effect = FileNotFoundError("zeit not found")

        with pytest.raises(RuntimeError, match="zeit not found"):
            ZeitIntegration()

    def test_init_raises_on_non_zero_exit(self, mock_subprocess):
        """Test that init raises error if zeit version fails."""
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="error")

        with pytest.raises(RuntimeError, match="not working"):
            ZeitIntegration()


class TestStartTracking:
    """Test start_tracking method."""

    def test_start_tracking_minimal(self, zeit_integration, mock_subprocess):
        """Test starting tracking with just a note."""
        mock_subprocess.return_value = Mock(returncode=0, stdout='{"status": "started"}', stderr="")

        result = zeit_integration.start_tracking(note="Working on tests")

        # Should call zeit start with note
        args = mock_subprocess.call_args[0][0]
        assert args[0] == "zeit"
        assert args[1] == "-f"
        assert args[2] == "json"
        assert "start" in args
        assert "-n" in args
        assert "Working on tests" in args
        assert result == {"status": "started"}

    def test_start_tracking_with_project_and_task(self, zeit_integration, mock_subprocess):
        """Test starting tracking with project and task."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        zeit_integration.start_tracking(note="Feature work", project="taskbridge", task="feat-123")

        args = mock_subprocess.call_args[0][0]
        assert "-p" in args
        assert "taskbridge" in args
        assert "-t" in args
        assert "feat-123" in args

    def test_start_tracking_with_start_time(self, zeit_integration, mock_subprocess):
        """Test starting tracking with custom start time."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        zeit_integration.start_tracking(note="Test", start_time="2 hours ago")

        args = mock_subprocess.call_args[0][0]
        assert "-s" in args
        assert "2 hours ago" in args


class TestStopTracking:
    """Test stop_tracking method."""

    def test_stop_tracking_basic(self, zeit_integration, mock_subprocess):
        """Test stopping tracking without options."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        result = zeit_integration.stop_tracking()

        args = mock_subprocess.call_args[0][0]
        assert "end" in args
        assert isinstance(result, dict)

    def test_stop_tracking_with_note(self, zeit_integration, mock_subprocess):
        """Test stopping tracking with a note."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        zeit_integration.stop_tracking(note="Completed feature")

        args = mock_subprocess.call_args[0][0]
        assert "-n" in args
        assert "Completed feature" in args

    def test_stop_tracking_with_end_time(self, zeit_integration, mock_subprocess):
        """Test stopping tracking with custom end time."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        zeit_integration.stop_tracking(end_time="5 minutes ago")

        args = mock_subprocess.call_args[0][0]
        assert "-e" in args
        assert "5 minutes ago" in args


class TestListBlocks:
    """Test list_blocks method."""

    def test_list_blocks_returns_timeblocks(self, zeit_integration, mock_subprocess):
        """Test listing blocks returns TimeBlock objects."""
        sample_blocks = [
            {
                "key": "block:123",
                "project_sid": "taskbridge",
                "task_sid": "test",
                "note": "Testing",
                "start": "2026-01-08T10:00:00-06:00",
                "end": "2026-01-08T11:00:00-06:00",
                "duration": 3600,
            }
        ]
        mock_subprocess.return_value = Mock(
            returncode=0, stdout=json.dumps(sample_blocks), stderr=""
        )

        blocks = zeit_integration.list_blocks()

        assert len(blocks) == 1
        assert isinstance(blocks[0], TimeBlock)
        assert blocks[0].key == "block:123"
        assert blocks[0].note == "Testing"

    def test_list_blocks_with_filters(self, zeit_integration, mock_subprocess):
        """Test listing blocks with filters."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="[]", stderr="")

        zeit_integration.list_blocks(project="taskbridge", start="today")

        args = mock_subprocess.call_args[0][0]
        assert "-p" in args
        assert "taskbridge" in args
        assert "-s" in args
        assert "today" in args

    def test_list_blocks_empty_result(self, zeit_integration, mock_subprocess):
        """Test listing blocks with no results."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="[]", stderr="")

        blocks = zeit_integration.list_blocks()

        assert blocks == []


class TestGetBlock:
    """Test get_block method."""

    def test_get_block_success(self, zeit_integration, mock_subprocess):
        """Test getting a specific block."""
        sample_block = [
            {
                "key": "block:123",
                "project_sid": "test",
                "task_sid": "task",
                "note": "Test",
                "start": "2026-01-08T10:00:00-06:00",
                "end": "2026-01-08T11:00:00-06:00",
                "duration": 3600,
            }
        ]
        mock_subprocess.return_value = Mock(
            returncode=0, stdout=json.dumps(sample_block), stderr=""
        )

        block = zeit_integration.get_block("block:123")

        assert block is not None
        assert isinstance(block, TimeBlock)
        assert block.key == "block:123"

    def test_get_block_not_found(self, zeit_integration, mock_subprocess):
        """Test getting a block that doesn't exist."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="[]", stderr="")

        block = zeit_integration.get_block("block:nonexistent")

        assert block is None


class TestEditBlock:
    """Test edit_block method."""

    def test_edit_block_note(self, zeit_integration, mock_subprocess):
        """Test editing a block's note."""
        mock_subprocess.return_value = Mock(
            returncode=0, stdout='{"success": true, "message": "Block updated!"}', stderr=""
        )

        result = zeit_integration.edit_block("block:123", note="Updated note")

        args = mock_subprocess.call_args[0][0]
        assert "block" in args
        assert "edit" in args
        assert "block:123" in args
        assert "-n" in args
        assert "Updated note" in args
        assert result["success"] is True

    def test_edit_block_multiple_fields(self, zeit_integration, mock_subprocess):
        """Test editing multiple fields of a block."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        zeit_integration.edit_block(
            "block:123",
            note="New note",
            project="newproject",
            task="newtask",
            start="2026-01-08T09:00:00",
            end="2026-01-08T10:00:00",
        )

        args = mock_subprocess.call_args[0][0]
        assert "-n" in args
        assert "-p" in args
        assert "-t" in args
        assert "-s" in args
        assert "-e" in args


class TestListProjects:
    """Test list_projects method."""

    def test_list_projects_returns_zeitprojects(self, zeit_integration, mock_subprocess):
        """Test listing projects returns ZeitProject objects."""
        sample_projects = [
            {
                "sid": "taskbridge",
                "display_name": "TASKBRIDGE",
                "color": "#ff0000",
                "total_blocks": 10,
                "total_amount": 36000,
                "tasks": [{"sid": "test", "display_name": "TEST", "color": "#00ff00"}],
            }
        ]
        mock_subprocess.return_value = Mock(
            returncode=0, stdout=json.dumps(sample_projects), stderr=""
        )

        projects = zeit_integration.list_projects()

        assert len(projects) == 1
        assert isinstance(projects[0], ZeitProject)
        assert projects[0].sid == "taskbridge"
        assert projects[0].total_blocks == 10

    def test_list_projects_empty(self, zeit_integration, mock_subprocess):
        """Test listing projects with no projects."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="[]", stderr="")

        projects = zeit_integration.list_projects()

        assert projects == []


class TestGetProject:
    """Test get_project method."""

    def test_get_project_found(self, zeit_integration, mock_subprocess):
        """Test getting a project that exists."""
        sample_projects = [
            {
                "sid": "taskbridge",
                "display_name": "TASKBRIDGE",
                "color": "#ff0000",
                "total_blocks": 5,
                "total_amount": 18000,
                "tasks": None,
            }
        ]
        mock_subprocess.return_value = Mock(
            returncode=0, stdout=json.dumps(sample_projects), stderr=""
        )

        project = zeit_integration.get_project("taskbridge")

        assert project is not None
        assert project.sid == "taskbridge"

    def test_get_project_not_found(self, zeit_integration, mock_subprocess):
        """Test getting a project that doesn't exist."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="[]", stderr="")

        project = zeit_integration.get_project("nonexistent")

        assert project is None


class TestGetStats:
    """Test get_stats method."""

    def test_get_stats_basic(self, zeit_integration, mock_subprocess):
        """Test getting basic stats."""
        sample_stats = {"taskbridge": {"test": {"2026-01-08": 3600}}}
        mock_subprocess.return_value = Mock(
            returncode=0, stdout=json.dumps(sample_stats), stderr=""
        )

        stats = zeit_integration.get_stats()

        assert isinstance(stats, dict)
        assert "taskbridge" in stats

    def test_get_stats_with_filters(self, zeit_integration, mock_subprocess):
        """Test getting stats with filters."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="{}", stderr="")

        zeit_integration.get_stats(project="taskbridge", start="this week")

        args = mock_subprocess.call_args[0][0]
        assert "stat" in args
        assert "-p" in args
        assert "taskbridge" in args
        assert "-s" in args
        assert "this week" in args


class TestExportData:
    """Test export_data method."""

    def test_export_data_to_string(self, zeit_integration, mock_subprocess):
        """Test exporting data to string."""
        export_output = "exported data"
        mock_subprocess.return_value = Mock(returncode=0, stdout=export_output, stderr="")

        result = zeit_integration.export_data()

        assert result == export_output

    def test_export_data_to_file(self, zeit_integration, mock_subprocess, tmp_path):
        """Test exporting data to file."""
        export_output = "exported data"
        mock_subprocess.return_value = Mock(returncode=0, stdout=export_output, stderr="")
        output_file = tmp_path / "export.json"

        result = zeit_integration.export_data(output_file=output_file)

        assert result == export_output
        assert output_file.read_text() == export_output

    def test_export_data_with_filters(self, zeit_integration, mock_subprocess):
        """Test exporting data with time filters."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="data", stderr="")

        zeit_integration.export_data(start="yesterday", end="today")

        args = mock_subprocess.call_args[0][0]
        assert "export" in args
        # Note: export doesn't use -f json flag
        assert "-s" in args
        assert "yesterday" in args
        assert "-e" in args
        assert "today" in args


class TestDataClasses:
    """Test TimeBlock and ZeitProject dataclasses."""

    def test_timeblock_from_dict(self):
        """Test creating TimeBlock from dict."""
        data = {
            "key": "block:123",
            "project_sid": "proj",
            "task_sid": "task",
            "note": "Test note",
            "start": "2026-01-08T10:00:00-06:00",
            "end": "2026-01-08T11:00:00-06:00",
            "duration": 3600,
        }

        block = TimeBlock.from_dict(data)

        assert block.key == "block:123"
        assert block.project_sid == "proj"
        assert block.note == "Test note"

    def test_zeitproject_from_dict(self):
        """Test creating ZeitProject from dict."""
        data = {
            "sid": "proj",
            "display_name": "PROJECT",
            "color": "#ff0000",
            "total_blocks": 5,
            "total_amount": 18000,
            "tasks": [{"sid": "task1", "display_name": "TASK1"}],
        }

        project = ZeitProject.from_dict(data)

        assert project.sid == "proj"
        assert project.display_name == "PROJECT"
        assert len(project.tasks) == 1

    def test_zeitproject_from_dict_no_tasks(self):
        """Test creating ZeitProject with null tasks."""
        data = {
            "sid": "proj",
            "display_name": "PROJECT",
            "color": "#ff0000",
            "total_blocks": 0,
            "total_amount": 0,
            "tasks": None,
        }

        project = ZeitProject.from_dict(data)

        assert project.tasks == []
