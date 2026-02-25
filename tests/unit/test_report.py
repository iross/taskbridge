"""Tests for time report aggregation and formatting."""

from datetime import datetime

import pytest

from taskbridge.database import Database, TaskTimeTracking


@pytest.fixture
def test_db(tmp_path):
    return Database(str(tmp_path / "test.db"))


# ============================================================================
# parse_project_segments
# ============================================================================


class TestParseProjectSegments:
    def test_client_and_project(self):
        from taskbridge.main import parse_project_segments

        assert parse_project_segments("CHTC::Morgridge-Seminar") == (
            "CHTC",
            "Morgridge-Seminar",
        )

    def test_tags_ignored(self):
        from taskbridge.main import parse_project_segments

        assert parse_project_segments("CHTC::Morgridge-Seminar::meeting") == (
            "CHTC",
            "Morgridge-Seminar",
        )

    def test_no_separator_goes_to_other(self):
        from taskbridge.main import parse_project_segments

        assert parse_project_segments("meetings") == ("(other)", "meetings")

    def test_multiple_tag_segments_ignored(self):
        from taskbridge.main import parse_project_segments

        assert parse_project_segments("CHTC::NAIRR::writing,urgent") == ("CHTC", "NAIRR")


# ============================================================================
# build_report_entries
# ============================================================================


class TestBuildReportEntries:
    def _record(self, project, description, started, stopped=None):
        return TaskTimeTracking(
            id=1,
            todoist_task_id="task-1",
            project_name=project,
            task_name=description,
            started_at=started,
            stopped_at=stopped,
        )

    def test_completed_session(self):
        from taskbridge.main import build_report_entries

        records = [
            self._record(
                "CHTC::NAIRR",
                "Write-up",
                datetime(2026, 2, 25, 9, 0),
                datetime(2026, 2, 25, 10, 0),
            )
        ]
        entries = build_report_entries(records, now=datetime(2026, 2, 25, 11, 0))

        assert len(entries) == 1
        assert entries[0].client == "CHTC"
        assert entries[0].project == "NAIRR"
        assert entries[0].seconds == 3600

    def test_active_session_uses_now(self):
        from taskbridge.main import build_report_entries

        records = [self._record("CHTC::NAIRR", "Write-up", datetime(2026, 2, 25, 9, 0))]
        now = datetime(2026, 2, 25, 9, 30)
        entries = build_report_entries(records, now=now)

        assert entries[0].seconds == 1800

    def test_skips_zero_duration(self):
        from taskbridge.main import build_report_entries

        records = [
            self._record(
                "CHTC::NAIRR",
                "Instant",
                datetime(2026, 2, 25, 9, 0),
                datetime(2026, 2, 25, 9, 0),
            )
        ]
        entries = build_report_entries(records, now=datetime(2026, 2, 25, 9, 0))

        assert entries == []

    def test_no_separator_maps_to_other(self):
        from taskbridge.main import build_report_entries

        records = [
            self._record(
                "meetings",
                "Team sync",
                datetime(2026, 2, 25, 9, 0),
                datetime(2026, 2, 25, 9, 30),
            )
        ]
        entries = build_report_entries(records, now=datetime(2026, 2, 25, 10, 0))

        assert entries[0].client == "(other)"
        assert entries[0].project == "meetings"


# ============================================================================
# format_report
# ============================================================================


class TestFormatReport:
    def _entry(self, client, project, description, seconds):
        from taskbridge.main import ReportEntry

        return ReportEntry(client=client, project=project, description=description, seconds=seconds)

    def test_empty(self):
        from taskbridge.main import format_report

        assert "No tracked time" in format_report([])

    def test_total_hours(self):
        from taskbridge.main import format_report

        entries = [self._entry("CHTC", "NAIRR", "Write-up", 3600)]
        output = format_report(entries)

        assert "Total: 1.0h" in output

    def test_client_fraction(self):
        from taskbridge.main import format_report

        entries = [
            self._entry("CHTC", "NAIRR", "Write-up", 3600),
            self._entry("PATh", "outreach", "Email", 3600),
        ]
        output = format_report(entries)

        assert "CHTC  0.50" in output
        assert "PATh  0.50" in output

    def test_project_fraction_of_client(self):
        from taskbridge.main import format_report

        entries = [
            self._entry("CHTC", "NAIRR", "Write-up", 2700),  # 45m
            self._entry("CHTC", "Standup", "Standup", 900),  # 15m
        ]
        output = format_report(entries)

        assert "NAIRR: 0.75" in output
        assert "Standup: 0.25" in output

    def test_descriptions_listed(self):
        from taskbridge.main import format_report

        entries = [self._entry("CHTC", "NAIRR", "Write-up", 3600)]
        output = format_report(entries)

        assert "    - Write-up" in output

    def test_clients_sorted_by_time_descending(self):
        from taskbridge.main import format_report

        entries = [
            self._entry("PATh", "proj", "task", 1800),
            self._entry("CHTC", "proj", "task", 3600),
        ]
        output = format_report(entries)

        assert output.index("CHTC") < output.index("PATh")


# ============================================================================
# get_tracking_in_range (database)
# ============================================================================


class TestGetTrackingInRange:
    def test_returns_records_in_range(self, test_db):
        test_db.create_tracking_record(
            todoist_task_id="t1",
            project_name="CHTC::NAIRR",
            task_name="Task",
            started_at=datetime(2026, 2, 25, 9, 0),
        )
        records = test_db.get_tracking_in_range(
            datetime(2026, 2, 25, 0, 0), datetime(2026, 2, 26, 0, 0)
        )
        assert len(records) == 1

    def test_excludes_records_outside_range(self, test_db):
        test_db.create_tracking_record(
            todoist_task_id="t1",
            project_name="CHTC::NAIRR",
            task_name="Task",
            started_at=datetime(2026, 2, 24, 9, 0),
        )
        records = test_db.get_tracking_in_range(
            datetime(2026, 2, 25, 0, 0), datetime(2026, 2, 26, 0, 0)
        )
        assert records == []

    def test_to_bound_is_exclusive(self, test_db):
        test_db.create_tracking_record(
            todoist_task_id="t1",
            project_name="CHTC::NAIRR",
            task_name="Task",
            started_at=datetime(2026, 2, 26, 0, 0),
        )
        records = test_db.get_tracking_in_range(
            datetime(2026, 2, 25, 0, 0), datetime(2026, 2, 26, 0, 0)
        )
        assert records == []
