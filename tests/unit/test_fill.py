"""Tests for time-gap filling helpers."""

from datetime import datetime

import pytest

from taskbridge.database import TaskTimeTracking
from taskbridge.main import (
    append_bartib_entry,
    find_workday_gaps,
    get_recent_projects,
    split_gap_by_events,
)


def _record(start: datetime, stop: datetime | None = None) -> TaskTimeTracking:
    return TaskTimeTracking(
        project_name="test::project",
        task_name="task",
        started_at=start,
        stopped_at=stop,
    )


def dt(h: int, m: int = 0, day: int = 27) -> datetime:
    return datetime(2026, 3, day, h, m)


WORK_START = dt(8)
WORK_END = dt(16)
NOW = dt(17)  # after end of day so active sessions count fully


class TestFindWorkdayGaps:
    def test_fully_empty_day(self):
        gaps = find_workday_gaps([], WORK_START, WORK_END, NOW)
        assert gaps == [(WORK_START, WORK_END)]

    def test_fully_tracked_day(self):
        records = [_record(dt(8), dt(16))]
        gaps = find_workday_gaps(records, WORK_START, WORK_END, NOW)
        assert gaps == []

    def test_gap_at_start(self):
        records = [_record(dt(9), dt(16))]
        gaps = find_workday_gaps(records, WORK_START, WORK_END, NOW)
        assert gaps == [(dt(8), dt(9))]

    def test_gap_at_end(self):
        records = [_record(dt(8), dt(15))]
        gaps = find_workday_gaps(records, WORK_START, WORK_END, NOW)
        assert gaps == [(dt(15), dt(16))]

    def test_gap_in_middle(self):
        records = [_record(dt(8), dt(10)), _record(dt(12), dt(16))]
        gaps = find_workday_gaps(records, WORK_START, WORK_END, NOW)
        assert gaps == [(dt(10), dt(12))]

    def test_multiple_gaps(self):
        records = [_record(dt(9), dt(10)), _record(dt(12), dt(14))]
        gaps = find_workday_gaps(records, WORK_START, WORK_END, NOW)
        assert gaps == [(dt(8), dt(9)), (dt(10), dt(12)), (dt(14), dt(16))]

    def test_min_gap_filters_short_gaps(self):
        # 20-minute gap: kept with default min_gap=15
        records = [_record(dt(8), dt(9, 20)), _record(dt(9, 40), dt(16))]
        gaps = find_workday_gaps(records, WORK_START, WORK_END, NOW, min_minutes=15)
        assert gaps == [(dt(9, 20), dt(9, 40))]

    def test_min_gap_drops_gap_below_threshold(self):
        # 10-minute gap: dropped when min_gap=15
        records = [_record(dt(8), dt(9, 10)), _record(dt(9, 20), dt(16))]
        gaps = find_workday_gaps(records, WORK_START, WORK_END, NOW, min_minutes=15)
        assert gaps == []

    def test_overlapping_records_merged(self):
        records = [_record(dt(8), dt(11)), _record(dt(10), dt(13))]
        gaps = find_workday_gaps(records, WORK_START, WORK_END, NOW)
        assert gaps == [(dt(13), dt(16))]

    def test_active_session_uses_now(self):
        # Active session from 8-? — with now=10:00 it covers 8-10
        now = dt(10)
        records = [_record(dt(8), None)]  # no stop time
        gaps = find_workday_gaps(records, WORK_START, WORK_END, now)
        assert gaps == [(dt(10), dt(16))]

    def test_records_outside_window_ignored(self):
        records = [_record(dt(6), dt(7)), _record(dt(17), dt(18))]
        gaps = find_workday_gaps(records, WORK_START, WORK_END, NOW)
        assert gaps == [(WORK_START, WORK_END)]


class _FakeEvent:
    def __init__(self, title: str, start: datetime, end: datetime):
        self.title = title
        self.start = start
        self.end = end


class TestSplitGapByEvents:
    def test_no_events_returns_single_block(self):
        blocks = split_gap_by_events(dt(9), dt(10), [])
        assert blocks == [(dt(9), dt(10), None)]

    def test_event_covers_full_gap(self):
        ev = _FakeEvent("Standup", dt(9), dt(10))
        blocks = split_gap_by_events(dt(9), dt(10), [ev])
        assert blocks == [(dt(9), dt(10), "Standup")]

    def test_event_covers_first_half(self):
        ev = _FakeEvent("Standup", dt(9), dt(9, 30))
        blocks = split_gap_by_events(dt(9), dt(10), [ev])
        assert (dt(9), dt(9, 30), "Standup") in blocks
        assert (dt(9, 30), dt(10), None) in blocks

    def test_two_events_no_overlap(self):
        ev1 = _FakeEvent("Meeting A", dt(9), dt(9, 30))
        ev2 = _FakeEvent("Meeting B", dt(9, 30), dt(10))
        blocks = split_gap_by_events(dt(9), dt(10), [ev1, ev2])
        titles = [b[2] for b in blocks]
        assert "Meeting A" in titles
        assert "Meeting B" in titles
        assert None not in titles

    def test_event_extends_beyond_gap_is_clamped(self):
        # Event 08:30 – 10:30, gap is 09:00 – 10:00
        ev = _FakeEvent("Long meeting", dt(8, 30), dt(10, 30))
        blocks = split_gap_by_events(dt(9), dt(10), [ev])
        assert blocks == [(dt(9), dt(10), "Long meeting")]

    def test_gap_with_uncovered_middle(self):
        ev1 = _FakeEvent("A", dt(9), dt(9, 20))
        ev2 = _FakeEvent("B", dt(9, 40), dt(10))
        blocks = split_gap_by_events(dt(9), dt(10), [ev1, ev2])
        titles = [b[2] for b in blocks]
        assert "A" in titles
        assert "B" in titles
        assert None in titles  # 09:20 – 09:40 uncovered


class TestGetRecentProjects:
    def test_returns_empty_for_missing_file(self):
        assert get_recent_projects("/nonexistent/path.bartib") == []

    def test_returns_unique_projects_most_recent_first(self, tmp_path):
        f = tmp_path / "activities.bartib"
        f.write_text(
            "2026-03-27 08:00 - 2026-03-27 09:00 | CHTC::htcondor | task1\n"
            "2026-03-27 09:00 - 2026-03-27 10:00 | PATh::admin | task2\n"
            "2026-03-27 10:00 - 2026-03-27 11:00 | CHTC::htcondor | task3\n"
        )
        projects = get_recent_projects(str(f))
        # Most recent first: last line is CHTC::htcondor, then PATh::admin
        assert projects[0] == "CHTC::htcondor"
        assert projects[1] == "PATh::admin"
        assert len(projects) == 2  # deduped

    def test_respects_limit(self, tmp_path):
        f = tmp_path / "activities.bartib"
        lines = "\n".join(
            f"2026-03-27 0{i}:00 - 2026-03-27 0{i}:30 | proj{i} | task" for i in range(8)
        )
        f.write_text(lines + "\n")
        projects = get_recent_projects(str(f), limit=3)
        assert len(projects) == 3


class TestAppendBartibEntry:
    def test_writes_correct_format(self, tmp_path, monkeypatch):
        f = tmp_path / "activities.bartib"
        f.write_text("")
        monkeypatch.setenv("BARTIB_FILE", str(f))

        append_bartib_entry(
            project="CHTC::htcondor",
            description="code review",
            start=datetime(2026, 3, 27, 9, 0),
            end=datetime(2026, 3, 27, 10, 30),
        )

        content = f.read_text()
        assert content == "2026-03-27 09:00 - 2026-03-27 10:30 | CHTC::htcondor | code review\n"

    def test_appends_to_existing_content(self, tmp_path, monkeypatch):
        f = tmp_path / "activities.bartib"
        f.write_text("2026-03-27 08:00 - 2026-03-27 09:00 | proj | existing\n")
        monkeypatch.setenv("BARTIB_FILE", str(f))

        append_bartib_entry(
            project="proj2",
            description="new",
            start=datetime(2026, 3, 27, 9, 0),
            end=datetime(2026, 3, 27, 10, 0),
        )

        lines = f.read_text().strip().splitlines()
        assert len(lines) == 2
        assert "existing" in lines[0]
        assert "new" in lines[1]

    def test_raises_without_bartib_file_env(self, monkeypatch):
        monkeypatch.delenv("BARTIB_FILE", raising=False)
        with pytest.raises(RuntimeError, match="BARTIB_FILE"):
            append_bartib_entry("proj", "desc", datetime(2026, 3, 27, 9), datetime(2026, 3, 27, 10))
