"""Tests for finding the commits and PRs behind a backlog task."""

import json
import subprocess
from unittest.mock import Mock

import pytest

from taskbridge import provenance
from taskbridge.provenance import RepoHistory, task_id_pattern

REAL_RUN = subprocess.run


def git(repo, *args):
    return REAL_RUN(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def commit(repo, path, message):
    file = repo / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(file.read_text() + "x\n" if file.exists() else "x\n")
    git(repo, "add", path)
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "proj"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "T")
    git(path, "remote", "add", "origin", "git@github.com:iross/proj.git")
    return path


def push(repo):
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")


@pytest.fixture
def gh(monkeypatch):
    """Fake gh: `prs` maps commit SHA to the PRs GitHub would report."""
    fake = Mock(prs={}, fail=False, calls=[])

    def run(cmd, **kwargs):
        if cmd[0] != "gh":
            return REAL_RUN(cmd, **kwargs)
        fake.calls.append(cmd)
        if fake.fail:
            return Mock(returncode=1, stdout="", stderr="HTTP 401: Bad credentials")
        sha = cmd[2].split("/")[-2]
        return Mock(returncode=0, stdout=json.dumps(fake.prs.get(sha, [])), stderr="")

    monkeypatch.setattr(provenance.subprocess, "run", run)
    monkeypatch.setattr(provenance.shutil, "which", lambda name: "/usr/bin/gh")
    return fake


class TestTaskIdPattern:
    @pytest.mark.parametrize(
        "text",
        ["task-9", "TASK-09 fix", "Fix it (Task-009)", "see task-9.", "task-9, task-10"],
    )
    def test_matches(self, text):
        assert task_id_pattern("TASK-9").search(text)

    @pytest.mark.parametrize(
        "text", ["task-90", "task-19", "task-9.1", "subtask-9", "my-task-9", "task9"]
    )
    def test_does_not_match(self, text):
        assert not task_id_pattern("task-09").search(text)

    def test_subtask_ids(self):
        pattern = task_id_pattern("TASK-9.1")
        assert pattern.search("task-09.01 done")
        assert not pattern.search("task-9.10")
        assert not pattern.search("task-9")


class TestCommitsFor:
    def test_matches_message_body_skips_bookkeeping_oldest_first(self, repo, gh):
        commit(repo, "src/a.py", "Add parser\n\nPart of task-4.")
        commit(repo, "backlog/tasks/task-4.md", "Mark task-4 done")
        commit(repo, "src/b.py", "Unrelated (task-43)")
        commit(repo, "backlog/tasks/task-4.md", "Fix TASK-4 docs")
        git(repo, "add", "-A")
        commit(repo, "src/c.py", "Wire parser (TASK-04)")

        commits = RepoHistory(repo).commits_for("TASK-4")

        assert [c.subject for c in commits] == ["Add parser", "Wire parser (TASK-04)"]

    def test_merge_commits_named_after_the_task_are_not_listed(self, repo, gh):
        commit(repo, "a.py", "Start")
        git(repo, "switch", "-q", "-c", "task-1-work")
        commit(repo, "b.py", "Implement it (task-1)")
        git(repo, "switch", "-q", "main")
        git(repo, "merge", "-q", "--no-ff", "task-1-work", "-m", "Merge branch 'task-1-work'")

        commits = RepoHistory(repo).commits_for("TASK-1")

        assert [c.subject for c in commits] == ["Implement it (task-1)"]

    def test_empty_commit_mentioning_the_task_is_listed(self, repo, gh):
        git(repo, "commit", "-q", "--allow-empty", "-m", "Deploy task-1 to production")

        assert [c.subject for c in RepoHistory(repo).commits_for("task-1")] == [
            "Deploy task-1 to production"
        ]

    def test_bookkeeping_on_non_ascii_task_files_is_skipped(self, repo, gh):
        commit(repo, "backlog/tasks/task-1 - Add-♾️-support.md", "Archive task-1")

        assert RepoHistory(repo).commits_for("task-1") == []

    def test_mixed_backlog_and_code_commit_counts(self, repo, gh):
        (repo / "backlog").mkdir()
        (repo / "backlog" / "t.md").write_text("x\n")
        (repo / "code.py").write_text("x\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "Do task-4 and update task file")

        assert len(RepoHistory(repo).commits_for("task-4")) == 1


class TestMarkdown:
    def test_no_matching_commits(self, repo, gh):
        commit(repo, "a.py", "Something else")

        assert RepoHistory(repo).markdown("TASK-1") is None

    def test_pushed_commits_link_unpushed_do_not(self, repo, gh):
        pushed = commit(repo, "a.py", "First (task-1)")
        push(repo)
        commit(repo, "a.py", "Second (task-1)")

        md = RepoHistory(repo).markdown("TASK-1")

        lines = md.splitlines()
        assert lines[0].startswith(
            f"- [{pushed[:7]}](https://github.com/iross/proj/commit/{pushed}) "
        )
        assert lines[0].endswith(" First (task-1)")
        assert lines[1].startswith("- `") and lines[1].endswith(" Second (task-1)")
        assert "github.com" not in lines[1]

    def test_lists_each_pr_once_and_only_asks_about_pushed_commits(self, repo, gh):
        a = commit(repo, "a.py", "One (task-1)")
        b = commit(repo, "a.py", "Two (task-1)")
        push(repo)
        commit(repo, "a.py", "Three (task-1)")
        pr = {
            "number": 9,
            "title": "Add [labels]",
            "html_url": "https://github.com/iross/proj/pull/9",
        }
        gh.prs = {a: [pr], b: [pr]}

        md = RepoHistory(repo).markdown("TASK-1")

        assert md.endswith(
            "Pull requests:\n\n- [#9 Add \\[labels\\]](https://github.com/iross/proj/pull/9)"
        )
        assert len(gh.calls) == 2

    def test_api_failure_warns_once_and_stops_asking(self, repo, gh):
        commit(repo, "a.py", "One (task-1)")
        commit(repo, "a.py", "Two (task-1)")
        push(repo)
        gh.fail = True
        history = RepoHistory(repo)

        md = history.markdown("TASK-1")

        assert "Pull requests" not in md
        assert len(md.splitlines()) == 2
        assert len(gh.calls) == 1
        assert history.warnings == [
            "GitHub lookup failed (HTTP 401: Bad credentials); pull requests skipped"
        ]

    def test_missing_gh_warns_and_still_links_commits(self, repo, gh, monkeypatch):
        sha = commit(repo, "a.py", "One (task-1)")
        push(repo)
        monkeypatch.setattr(provenance.shutil, "which", lambda name: None)
        history = RepoHistory(repo)

        md = history.markdown("TASK-1")

        assert f"commit/{sha}" in md
        assert gh.calls == []
        assert history.warnings == ["gh not found; pull requests are not listed"]

    @pytest.mark.parametrize("remote", ["https://gitlab.com/iross/proj.git", None])
    def test_non_github_remote_shows_short_shas(self, repo, gh, remote):
        git(repo, "remote", "remove", "origin")
        if remote:
            git(repo, "remote", "add", "origin", remote)
        sha = commit(repo, "a.py", "One (task-1)")
        push(repo)
        history = RepoHistory(repo)

        assert history.markdown("TASK-1").startswith(f"- `{sha[:7]}` ")
        assert gh.calls == []
        assert history.warnings == ["origin is not a GitHub remote; commits get no links or PRs"]

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/iross/proj.git",
            "https://github.com/iross/proj",
            "git@github.com:iross/proj.git",
            "ssh://git@github.com/iross/proj.git",
        ],
    )
    def test_github_remote_forms(self, repo, gh, url):
        git(repo, "remote", "set-url", "origin", url)

        assert RepoHistory(repo).github == "iross/proj"

    def test_not_a_git_repo(self, tmp_path, gh):
        history = RepoHistory(tmp_path)

        assert history.markdown("TASK-1") is None
        assert "not a git repository" in history.warnings[0]
