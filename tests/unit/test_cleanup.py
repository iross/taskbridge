"""Tests for merging near-duplicate task names in the bartib log (time cleanup)."""

from datetime import datetime

import pytest
from typer.testing import CliRunner

from taskbridge.cleanup import cluster_similar_names, names_similar
from taskbridge.main import (
    app,
    apply_cleanup_mapping,
    build_report_entries,
    find_cleanup_clusters,
    format_report,
    parse_bartib_file,
)

NOW = datetime(2026, 11, 2, 12, 0)

LOG = (
    "# comment header\n"
    "\n"
    "2026-10-01 09:00 - 2026-10-01 10:00 | CHTC::htcondor | Review PR #review\n"
    "2026-10-02 09:00 - 2026-10-02 09:30 | CHTC::htcondor | Review PRs #docs\n"
    "2026-10-03 09:00 - 2026-10-03 09:20 | CHTC::htcondor | review pr\n"
    "2026-10-03 10:00 - 2026-10-03 10:45 | CHTC::htcondor | Sprint 12 planning\n"
    "2026-10-03 11:00 - 2026-10-03 11:45 | CHTC::htcondor | Sprint 13 planning\n"
    "2026-10-04 09:00 - 2026-10-04 09:30 | OTHER::site | Review PRs\n"
)


class TestSimilarity:
    @pytest.mark.parametrize(
        "a,b",
        [
            ("Review PR", "Review PRs"),
            ("Review PR", "review  pr"),
            ("Weekly sync!", "weekly sync"),
        ],
    )
    def test_similar(self, a, b):
        assert names_similar(a, b)

    @pytest.mark.parametrize(
        "a,b",
        [
            ("Sprint 12 planning", "Sprint 13 planning"),
            ("Fix bug 101", "Fix bug 1010"),
            ("Write docs", "Deploy cluster"),
        ],
    )
    def test_not_similar(self, a, b):
        assert not names_similar(a, b)

    def test_groups_attach_to_first_name_not_chain(self):
        # "aaaaaaaaaa" ~ "aaaaaaaaab" ~ "aaaaaaaabb", but the 3rd is too far from the 1st.
        names = ["aaaaaaaaaa", "aaaaaaaaab", "aaaaaaaabb"]
        assert cluster_similar_names(names, threshold=0.9) == [["aaaaaaaaaa", "aaaaaaaaab"]]

    def test_singletons_dropped(self):
        assert cluster_similar_names(["alpha", "completely different"]) == []


class TestFindClusters:
    def test_clusters_within_project_only_and_ordered_by_time(self):
        lines: list[str] = LOG.splitlines(keepends=True)
        clusters = find_cleanup_clusters(lines, NOW)
        assert len(clusters) == 1  # OTHER::site's lone "Review PRs" is not merged across projects
        cluster = clusters[0]
        assert (cluster.client, cluster.project) == ("CHTC", "htcondor")
        # Most tracked time first; tags are not part of the name.
        assert [(v.name, v.count, v.seconds) for v in cluster.variants] == [
            ("Review PR", 1, 3600),
            ("Review PRs", 1, 1800),
            ("review pr", 1, 1200),
        ]


class TestApplyMapping:
    MAPPING = {
        ("CHTC", "htcondor", "Review PRs"): "Review PR",
        ("CHTC", "htcondor", "review pr"): "Review PR",
    }

    def test_rewrites_only_mapped_entries_and_keeps_tags_and_other_lines(self):
        lines: list[str] = LOG.splitlines(keepends=True)
        new_lines, changed = apply_cleanup_mapping(lines, self.MAPPING, NOW)
        assert changed == 2
        expected = list(lines)
        expected[3] = "2026-10-02 09:00 - 2026-10-02 09:30 | CHTC::htcondor | Review PR #docs\n"
        expected[4] = "2026-10-03 09:00 - 2026-10-03 09:20 | CHTC::htcondor | Review PR\n"
        assert new_lines == expected  # comment, blank, other project, sprint lines untouched

    def test_preserves_missing_trailing_newline(self):
        lines = ["2026-10-02 09:00 - 2026-10-02 09:30 | CHTC::htcondor | Review PRs"]
        new_lines, _ = apply_cleanup_mapping(lines, self.MAPPING, NOW)
        assert new_lines == ["2026-10-02 09:00 - 2026-10-02 09:30 | CHTC::htcondor | Review PR"]

    def test_renames_running_entry(self):
        lines = ["2026-11-02 11:00 | CHTC::htcondor | Review PRs #docs\n"]
        new_lines, changed = apply_cleanup_mapping(lines, self.MAPPING, NOW)
        assert changed == 1
        assert new_lines == ["2026-11-02 11:00 | CHTC::htcondor | Review PR #docs\n"]

    def test_mapping_is_not_applied_to_other_projects(self):
        lines = ["2026-10-04 09:00 - 2026-10-04 09:30 | OTHER::site | Review PRs\n"]
        assert apply_cleanup_mapping(lines, self.MAPPING, NOW) == (lines, 0)

    def test_mapping_applies_to_every_raw_spelling_of_the_same_report_project(self, monkeypatch):
        from taskbridge.main import config_manager

        monkeypatch.setattr(config_manager, "resolve_client_name", lambda n: n.upper())
        lines = [
            "2026-10-02 09:00 - 2026-10-02 09:30 | chtc::htcondor | Review PRs\n",
            "2026-10-02 10:00 - 2026-10-02 10:30 | CHTC::htcondor | Review PRs\n",
        ]
        _, changed = apply_cleanup_mapping(lines, self.MAPPING, NOW)
        assert changed == 2


class TestReportAfterCleanup:
    def test_report_merges_rows_and_keeps_total(self, tmp_path, monkeypatch):
        path = tmp_path / "activities.bartib"
        path.write_text(LOG)
        monkeypatch.setenv("BARTIB_FILE", str(path))

        def report_rows():
            records = parse_bartib_file(datetime.min, datetime.max)
            entries = build_report_entries(records, now=NOW)
            return format_report(entries), sum(e.seconds for e in entries)

        before, total_before = report_rows()
        assert "Review PRs" in before

        new_lines, _ = apply_cleanup_mapping(
            path.read_text().splitlines(keepends=True), TestApplyMapping.MAPPING, NOW
        )
        path.write_text("".join(new_lines))
        after, total_after = report_rows()

        assert total_after == total_before
        assert after.count("Review PRs") == 1  # only OTHER::site's, a different project
        review_row = next(line for line in after.splitlines() if "Review PR " in line)
        assert "1h 50m" in review_row  # 60 + 30 + 20 minutes, tag pills notwithstanding


class TestCleanupCommand:
    @pytest.fixture
    def bartib(self, tmp_path, monkeypatch):
        path = tmp_path / "activities.bartib"
        path.write_text(LOG)
        monkeypatch.setenv("BARTIB_FILE", str(path))
        return path

    def run(self, *args, input):
        return CliRunner().invoke(app, ["time", "cleanup", *args], input=input)

    def test_accept_and_confirm_rewrites_with_backup(self, bartib):
        result = self.run(input="y\ny\n")
        assert result.exit_code == 0, result.output
        text = bartib.read_text()
        assert "CHTC::htcondor | Review PRs" not in text and "review pr\n" not in text
        assert text.count("CHTC::htcondor | Review PR") == 3
        backups = list(bartib.parent.glob("activities.bartib.bak-*"))
        assert len(backups) == 1 and backups[0].read_text() == LOG

    def test_skip_writes_nothing(self, bartib):
        result = self.run(input="n\n")
        assert result.exit_code == 0
        assert "Nothing to merge" in result.output
        assert bartib.read_text() == LOG
        assert not list(bartib.parent.glob("*.bak-*"))

    def test_declining_confirmation_writes_nothing(self, bartib):
        result = self.run(input="y\nn\n")
        assert "Cancelled" in result.output
        assert bartib.read_text() == LOG

    def test_dry_run_never_writes(self, bartib):
        result = self.run("--dry-run", input="y\n")
        assert "2 bartib entries would be rewritten" in result.output
        assert bartib.read_text() == LOG
        assert not list(bartib.parent.glob("*.bak-*"))

    def test_choose_other_name_as_canonical(self, bartib):
        # Pick variant 2 ("Review PRs") as the name to keep.
        result = self.run(input="2\ny\ny\n")
        assert result.exit_code == 0, result.output
        text = bartib.read_text()
        assert text.count("CHTC::htcondor | Review PRs") == 3
        assert "| Review PR #review" not in text

    def test_edit_name_rejects_tags_then_accepts(self, bartib):
        result = self.run(input="e\nBad #tag\ne\nCode review\ny\ny\n")
        assert "no #tags" in result.output
        text = bartib.read_text()
        assert text.count("| Code review") == 3
        assert "Code review #review" in text and "Code review #docs" in text

    def test_select_subset(self, bartib):
        # Merge only variants 1 and 2; the lowercase one stays.
        result = self.run(input="s\n1,2\ny\ny\n")
        assert result.exit_code == 0, result.output
        text = bartib.read_text()
        assert "| review pr\n" in text
        assert "CHTC::htcondor | Review PRs" not in text

    def test_quit_stops_review_and_writes_nothing(self, bartib):
        result = self.run(input="q\n")
        assert "Nothing to merge" in result.output
        assert bartib.read_text() == LOG

    def test_missing_env_var(self, monkeypatch):
        monkeypatch.delenv("BARTIB_FILE", raising=False)
        result = self.run(input="")
        assert result.exit_code == 1
        assert "BARTIB_FILE" in result.output
