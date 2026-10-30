"""Where a backlog task's work happened: the commits that mention it and their PRs.

The repo's history is read once per archive run; PRs come from GitHub through
the gh CLI. Anything that keeps PRs from being found (no gh, not a GitHub
remote, an API failure) becomes a warning, never an error.
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

_RECORD, _FIELD = "\x1e", "\x1f"
_LOG_FORMAT = _RECORD + _FIELD.join(["%H", "%h", "%ad", "%s", "%B"]) + _FIELD
_GITHUB_REMOTE_RE = re.compile(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")


@dataclass
class Commit:
    """A non-merge commit, with the files it changed."""

    sha: str
    short: str
    date: str
    subject: str
    message: str
    files: list[str]


@dataclass
class PullRequest:
    """A GitHub pull request containing a commit."""

    number: int
    title: str
    url: str


def task_id_pattern(task_id: str) -> re.Pattern[str]:
    """Matches a task ID in prose: any case, any zero padding, not part of a longer ID."""
    bare = re.sub(r"^task-", "", task_id.strip(), flags=re.IGNORECASE)
    numbers = [part.lstrip("0") or "0" for part in bare.split(".")]
    body = r"\.".join("0*" + re.escape(number) for number in numbers)
    return re.compile(rf"(?<![\w-])task-{body}(?!\d|\.\d)", re.IGNORECASE)


def _link_text(text: str) -> str:
    return text.replace("[", "\\[").replace("]", "\\]")


def _git(repo: Path, *args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def _parse_log(output: str) -> list[Commit]:
    commits = []
    for record in output.split(_RECORD)[1:]:
        sha, short, date, subject, message, files = record.split(_FIELD)
        commits.append(
            Commit(sha, short, date, subject, message, [f for f in files.splitlines() if f])
        )
    return list(reversed(commits))


def _is_bookkeeping(commit: Commit) -> bool:
    """A commit that only edits backlog task files, like marking a task done."""
    return bool(commit.files) and all(path.startswith("backlog/") for path in commit.files)


class RepoHistory:
    """A repo's commits and GitHub links, read once and queried per task."""

    def __init__(self, repo: Path):
        self.warnings: list[str] = []
        self.commits: list[Commit] = []
        self.github: str | None = None
        self._pushed: set[str] = set()
        self._pr_cache: dict[str, list[PullRequest]] = {}
        self._prs_enabled = False
        if _git(repo, "rev-parse", "--git-dir") is None:
            self.warnings.append(f"{repo} is not a git repository; no provenance added")
            return
        log_args = ["log", "--no-merges", "--date=short", f"--format={_LOG_FORMAT}", "--name-only"]
        # Unquoted paths, so non-ASCII task filenames still start with "backlog/"
        log_args = ["-c", "core.quotePath=false", *log_args]
        self.commits = _parse_log(_git(repo, *log_args) or "")
        self._pushed = set((_git(repo, "rev-list", "--remotes") or "").split())
        self._find_github(repo)

    def _find_github(self, repo: Path) -> None:
        remote = (_git(repo, "remote", "get-url", "origin") or "").strip()
        match = _GITHUB_REMOTE_RE.search(remote)
        if not match:
            self.warnings.append("origin is not a GitHub remote; commits get no links or PRs")
            return
        self.github = f"{match.group(1)}/{match.group(2)}"
        if shutil.which("gh") is None:
            self.warnings.append("gh not found; pull requests are not listed")
            return
        self._prs_enabled = True

    def commits_for(self, task_id: str) -> list[Commit]:
        """Commits whose message mentions the task, except backlog-only bookkeeping."""
        pattern = task_id_pattern(task_id)
        return [
            commit
            for commit in self.commits
            if pattern.search(commit.message) and not _is_bookkeeping(commit)
        ]

    def _pull_requests(self, commit: Commit) -> list[PullRequest]:
        if not self._prs_enabled or commit.sha not in self._pushed:
            return []
        if commit.sha not in self._pr_cache:
            endpoint = f"repos/{self.github}/commits/{commit.sha}/pulls"
            result = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True)
            if result.returncode != 0:
                self._prs_enabled = False
                reason = (result.stderr.strip().splitlines() or ["unknown error"])[-1]
                self.warnings.append(f"GitHub lookup failed ({reason}); pull requests skipped")
                return []
            self._pr_cache[commit.sha] = [
                PullRequest(pr["number"], pr["title"], pr["html_url"])
                for pr in json.loads(result.stdout)
            ]
        return self._pr_cache[commit.sha]

    def _commit_line(self, commit: Commit) -> str:
        ref = f"`{commit.short}`"
        if self.github and commit.sha in self._pushed:
            ref = f"[{commit.short}](https://github.com/{self.github}/commit/{commit.sha})"
        return f"- {ref} {commit.date} {commit.subject}"

    def markdown(self, task_id: str) -> str | None:
        """The Provenance subsection body for a task, or None if no commits mention it."""
        commits = self.commits_for(task_id)
        if not commits:
            return None
        lines = [self._commit_line(commit) for commit in commits]
        pulls: dict[int, PullRequest] = {}
        for commit in commits:
            for pr in self._pull_requests(commit):
                pulls.setdefault(pr.number, pr)
        if pulls:
            lines += ["", "Pull requests:", ""]
            lines += [f"- [#{pr.number} {_link_text(pr.title)}]({pr.url})" for pr in pulls.values()]
        return "\n".join(lines)
