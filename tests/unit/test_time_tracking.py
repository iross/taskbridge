"""Tests for time tracking database operations and helper functions."""

from datetime import datetime
from unittest.mock import patch

import pytest

from taskbridge.database import Database, TaskTimeTracking


@pytest.fixture
def test_db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def sample_tracking_record():
    """Sample tracking record."""
    return TaskTimeTracking(
        id=1,
        todoist_task_id="task-123",
        project_name="taskbridge",
        task_name="Test Task",
        started_at=datetime(2026, 1, 8, 10, 0, 0),
        stopped_at=None,
        created_at=datetime(2026, 1, 8, 10, 0, 0),
        updated_at=datetime(2026, 1, 8, 10, 0, 0),
    )


class TestCreateTrackingRecord:
    """Test create_tracking_record database method."""

    def test_create_tracking_record_basic(self, test_db):
        """Test creating a basic tracking record."""
        started_at = datetime(2026, 1, 8, 10, 0, 0)

        record_id = test_db.create_tracking_record(
            todoist_task_id="task-123",
            project_name="taskbridge",
            task_name="Test Task",
            started_at=started_at,
        )

        assert record_id is not None
        assert record_id > 0

    def test_create_tracking_record_auto_timestamp(self, test_db):
        """Test that started_at defaults to now if not provided."""
        record_id = test_db.create_tracking_record(
            todoist_task_id="task-789", project_name="proj", task_name="Task"
        )

        assert record_id is not None

        # Verify record was created with timestamp
        record = test_db.get_tracking_by_task_id("task-789")
        assert record is not None
        assert record.started_at is not None


class TestGetActiveTracking:
    """Test get_active_tracking database method."""

    def test_get_active_tracking_returns_active(self, test_db):
        """Test getting active tracking (stopped_at is None)."""
        # Create active tracking
        test_db.create_tracking_record(
            todoist_task_id="task-active", project_name="proj", task_name="Active Task"
        )

        active = test_db.get_active_tracking()

        assert active is not None
        assert active.todoist_task_id == "task-active"
        assert active.stopped_at is None

    def test_get_active_tracking_ignores_stopped(self, test_db):
        """Test that get_active_tracking ignores stopped sessions."""
        # Create and stop a tracking session
        test_db.create_tracking_record(
            todoist_task_id="task-stopped", project_name="proj", task_name="Stopped Task"
        )
        stopped = test_db.get_tracking_by_task_id("task-stopped")
        test_db.update_tracking_record(stopped, stopped_at=datetime.now())

        active = test_db.get_active_tracking()

        assert active is None

    def test_get_active_tracking_returns_most_recent(self, test_db):
        """Test that get_active_tracking returns most recent active session."""
        # Create two active sessions
        test_db.create_tracking_record(
            todoist_task_id="task-1", project_name="proj", task_name="Task 1"
        )
        test_db.create_tracking_record(
            todoist_task_id="task-2", project_name="proj", task_name="Task 2"
        )

        active = test_db.get_active_tracking()

        # Should return the most recent one
        assert active.todoist_task_id == "task-2"


class TestGetTrackingByTaskId:
    """Test get_tracking_by_task_id database method."""

    def test_get_tracking_by_task_id_found(self, test_db):
        """Test getting tracking record by task ID."""
        test_db.create_tracking_record(
            todoist_task_id="task-123", project_name="proj", task_name="Test"
        )

        record = test_db.get_tracking_by_task_id("task-123")

        assert record is not None
        assert record.todoist_task_id == "task-123"

    def test_get_tracking_by_task_id_not_found(self, test_db):
        """Test getting tracking for non-existent task."""
        record = test_db.get_tracking_by_task_id("nonexistent")

        assert record is None

    def test_get_tracking_by_task_id_returns_most_recent(self, test_db):
        """Test that it returns the most recent record for a task."""
        # Create two records for same task
        first_time = datetime(2026, 1, 8, 10, 0, 0)
        second_time = datetime(2026, 1, 8, 11, 0, 0)

        test_db.create_tracking_record(
            todoist_task_id="task-123",
            project_name="proj",
            task_name="Test",
            started_at=first_time,
        )
        test_db.create_tracking_record(
            todoist_task_id="task-123",
            project_name="proj",
            task_name="Test",
            started_at=second_time,
        )

        record = test_db.get_tracking_by_task_id("task-123")

        # Should return the one started at 11:00
        assert record.started_at == second_time


class TestGetAllTrackingForTask:
    """Test get_all_tracking_for_task database method."""

    def test_get_all_tracking_for_task(self, test_db):
        """Test getting all tracking records for a task."""
        # Create multiple records
        test_db.create_tracking_record(
            todoist_task_id="task-123",
            project_name="proj",
            task_name="Test",
            started_at=datetime(2026, 1, 8, 10, 0, 0),
        )
        test_db.create_tracking_record(
            todoist_task_id="task-123",
            project_name="proj",
            task_name="Test",
            started_at=datetime(2026, 1, 8, 11, 0, 0),
        )

        records = test_db.get_all_tracking_for_task("task-123")

        assert len(records) == 2
        # Should be ordered by started_at DESC
        assert records[0].started_at > records[1].started_at

    def test_get_all_tracking_for_task_empty(self, test_db):
        """Test getting all tracking for task with no records."""
        records = test_db.get_all_tracking_for_task("nonexistent")

        assert records == []


class TestUpdateTrackingRecord:
    """Test update_tracking_record database method."""

    def test_update_tracking_record_with_stop_time(self, test_db):
        """Test updating tracking record with stop time."""
        # Create active tracking
        test_db.create_tracking_record(
            todoist_task_id="task-123", project_name="proj", task_name="Test"
        )
        record = test_db.get_tracking_by_task_id("task-123")
        assert record.stopped_at is None

        # Update with stop time
        stopped_at = datetime(2026, 1, 8, 12, 0, 0)
        success = test_db.update_tracking_record(record, stopped_at=stopped_at)

        assert success is True

        # Verify update
        updated = test_db.get_tracking_by_task_id("task-123")
        assert updated.stopped_at == stopped_at

    def test_update_tracking_record_auto_timestamp(self, test_db):
        """Test update with auto-generated timestamp."""
        test_db.create_tracking_record(
            todoist_task_id="task-456", project_name="proj", task_name="Test"
        )
        record = test_db.get_tracking_by_task_id("task-456")

        # Update without providing stop time
        success = test_db.update_tracking_record(record)

        assert success is True

        # Should have stopped_at set
        updated = test_db.get_tracking_by_task_id("task-456")
        assert updated.stopped_at is not None

    def test_update_tracking_record_without_id_fails(self, test_db):
        """Test that updating record without ID fails."""
        record = TaskTimeTracking(todoist_task_id="task-123", project_name="proj", task_name="Test")

        success = test_db.update_tracking_record(record)

        assert success is False


class TestHelperFunctions:
    """Test time tracking helper functions from main.py."""

    def test_format_duration_hours_and_minutes(self):
        """Test formatting duration with hours and minutes."""
        from taskbridge.main import format_duration

        # 2 hours 30 minutes = 9000 seconds
        result = format_duration(9000)

        assert result == "2h 30m"

    def test_format_duration_minutes_only(self):
        """Test formatting duration with only minutes."""
        from taskbridge.main import format_duration

        # 45 minutes = 2700 seconds
        result = format_duration(2700)

        assert result == "45m"

    def test_format_duration_zero(self):
        """Test formatting zero duration."""
        from taskbridge.main import format_duration

        result = format_duration(0)

        assert result == "0m"

    def test_format_duration_rounds_minutes(self):
        """Test that duration rounds down partial minutes."""
        from taskbridge.main import format_duration

        # 1h 15m 30s = 4530 seconds -> should show as 1h 15m
        result = format_duration(4530)

        assert result == "1h 15m"

    def test_sanitize_project_name_basic(self):
        """Test sanitizing basic project name."""
        from taskbridge.main import sanitize_project_name

        result = sanitize_project_name("My Project")

        assert result == "my-project"

    def test_sanitize_project_name_with_emojis(self):
        """Test sanitizing project name with emojis."""
        from taskbridge.main import sanitize_project_name

        result = sanitize_project_name("🌲 🦨 Project")

        # Emojis should be removed
        assert result == "project"

    def test_sanitize_project_name_with_special_chars(self):
        """Test sanitizing project name with special characters."""
        from taskbridge.main import sanitize_project_name

        result = sanitize_project_name("Test@#$%Project!")

        assert result == "testproject"

    def test_sanitize_project_name_multiple_spaces(self):
        """Test sanitizing project name with multiple spaces."""
        from taskbridge.main import sanitize_project_name

        result = sanitize_project_name("My   Big   Project")

        # Multiple spaces should become single hyphen
        assert result == "my-big-project"

    def test_sanitize_project_name_already_clean(self):
        """Test sanitizing already clean project name."""
        from taskbridge.main import sanitize_project_name

        result = sanitize_project_name("taskbridge-project")

        assert result == "taskbridge-project"

    def test_sanitize_project_name_empty_result(self):
        """Test sanitizing name that becomes empty."""
        from taskbridge.main import sanitize_project_name

        result = sanitize_project_name("🌲🦨")

        # Should default to "general"
        assert result == "general"

    def test_build_bartib_project_with_client(self):
        """Test building bartib project name with client."""
        from taskbridge.main import build_bartib_project

        result = build_bartib_project("My Project", "Acme Corp")

        assert result == "acme-corp::my-project"

    def test_build_bartib_project_without_client(self):
        """Test building bartib project name without client."""
        from taskbridge.main import build_bartib_project

        result = build_bartib_project("My Project")

        assert result == "my-project"

    def test_build_bartib_project_with_tags(self):
        """Test building bartib project name with tags."""
        from taskbridge.main import build_bartib_project

        result = build_bartib_project("My Project", "Acme Corp", tags=["work", "urgent"])

        assert result == "acme-corp::my-project::work,urgent"

    def test_build_bartib_project_with_tags_no_client(self):
        """Test building bartib project name with tags but no client."""
        from taskbridge.main import build_bartib_project

        result = build_bartib_project("My Project", tags=["billable"])

        assert result == "my-project::billable"

    def test_build_bartib_project_no_tags(self):
        """Test building bartib project name with empty tags list."""
        from taskbridge.main import build_bartib_project

        result = build_bartib_project("My Project", "Client", tags=[])

        assert result == "client::my-project"


class TestStopTrackingInternal:
    """Test stop_tracking_internal helper function."""

    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.TodoistAPI")
    @patch("taskbridge.main.db")
    def test_stop_tracking_internal_success(self, mock_db, mock_api_class, mock_bartib_class):
        """Test successful stop tracking internal."""
        from taskbridge.main import stop_tracking_internal

        started = datetime(2026, 1, 8, 10, 0, 0)
        stopped = datetime(2026, 1, 8, 11, 0, 0)

        tracking = TaskTimeTracking(
            id=1,
            todoist_task_id="task-123",
            project_name="proj",
            task_name="Test",
            started_at=started,
        )

        with patch("taskbridge.main.datetime") as mock_dt:
            mock_dt.now.return_value = stopped
            success, duration = stop_tracking_internal(tracking)

        assert success is True
        assert duration == 3600  # 1 hour
        mock_bartib_class.return_value.stop_tracking.assert_called_once_with()
        mock_db.update_tracking_record.assert_called_once()

    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.db")
    def test_stop_tracking_internal_adds_todoist_comment(self, mock_db, mock_bartib_class):
        """Test that Todoist comment is added with duration."""
        from taskbridge.main import stop_tracking_internal

        started = datetime(2026, 1, 8, 10, 0, 0)
        stopped = datetime(2026, 1, 8, 12, 30, 0)  # 2.5 hours

        tracking = TaskTimeTracking(
            id=1,
            todoist_task_id="task-123",
            project_name="proj",
            task_name="Test",
            started_at=started,
        )

        with patch("taskbridge.main.datetime") as mock_dt:
            mock_dt.now.return_value = stopped
            with patch("taskbridge.main.TodoistAPI") as mock_api_class:
                mock_api = mock_api_class.return_value
                success, duration = stop_tracking_internal(tracking)

                # Should add comment with formatted duration (2h 30m)
                mock_api.create_comment.assert_called_once()
                call_args = mock_api.create_comment.call_args
                assert "task-123" in call_args[0]
                assert "2h 30m" in call_args[0][1]

    @patch("taskbridge.main.BartibIntegration")
    @patch("taskbridge.main.db")
    def test_stop_tracking_internal_handles_errors(self, mock_db, mock_bartib_class):
        """Test that errors are handled gracefully."""
        from taskbridge.main import stop_tracking_internal

        # Make bartib raise an error
        mock_bartib_class.side_effect = Exception("Bartib failed")

        tracking = TaskTimeTracking(
            id=1,
            todoist_task_id="task-123",
            project_name="proj",
            task_name="Test",
            started_at=datetime(2026, 1, 8, 10, 0, 0),
        )

        success, duration = stop_tracking_internal(tracking)

        assert success is False
        assert duration == 0
