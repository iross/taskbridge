"""Links between backlog.md tasks and their parent Todoist task (ADR-004).

A backlog task names its parent with a Todoist task URL in its frontmatter
`references` list. The backlog CLI cannot edit tasks in `completed/`, so the
references key is rewritten here directly, leaving the rest of the file as is.
"""

import re
from pathlib import Path

from . import frontmatter

TODOIST_TASK_URL = "https://app.todoist.com/app/task/{}"
_TODOIST_TASK_URL_RE = re.compile(
    r"^https://app\.todoist\.com/app/task/(?:[^/?#]*-)?([A-Za-z0-9]+)/?$"
)
_TASK_DIRS = ("tasks", "completed")


class BacklogError(Exception):
    """A backlog task could not be found, read or updated."""


def todoist_task_url(task_id: str) -> str:
    """The canonical URL stored in references for a Todoist task."""
    return TODOIST_TASK_URL.format(task_id)


def todoist_task_id(reference: str) -> str | None:
    """The Todoist task ID in a reference, or None if it is not a Todoist task URL.

    Accepts the canonical form and the browser form `.../task/<slug>-<id>`;
    Todoist IDs contain no hyphens, so the ID is whatever follows the last one.
    """
    match = _TODOIST_TASK_URL_RE.match(reference.strip())
    return match.group(1) if match else None


def _normalize_task_id(task_id: str) -> str:
    """'TASK-09', 'task-9' and '9' all become '9'; subtask '42.01' becomes '42.1'."""
    bare = re.sub(r"^task-", "", task_id.strip(), flags=re.IGNORECASE)
    return ".".join(part.lstrip("0") or "0" for part in bare.split("."))


def task_files(repo: Path) -> list[Path]:
    """Every task file in the repo's backlog/tasks and backlog/completed."""
    backlog_dir = repo / "backlog"
    if not backlog_dir.is_dir():
        raise BacklogError(f"No backlog/ directory in {repo.resolve()}. Pass --repo.")
    return [path for sub in _TASK_DIRS for path in sorted((backlog_dir / sub).glob("task-*.md"))]


def task_number(path: Path) -> tuple[int, ...]:
    """Sort key for a task file: TASK-9 before TASK-10, TASK-9.2 after TASK-9."""
    normalized = _normalize_task_id(path.name.split(" ", 1)[0].removesuffix(".md"))
    return tuple(int(part) if part.isdigit() else 0 for part in normalized.split("."))


def find_task_file(repo: Path, task_id: str) -> Path:
    """Locate a backlog task's file in the repo's backlog/tasks or backlog/completed."""
    wanted = _normalize_task_id(task_id)
    for path in task_files(repo):
        if _normalize_task_id(path.name.split(" ", 1)[0].removesuffix(".md")) == wanted:
            return path
    raise BacklogError(f"Backlog task {task_id} not found in {(repo / 'backlog').resolve()}.")


def _frontmatter(path: Path) -> tuple[list[str], str]:
    try:
        lines, body = frontmatter.split(path.read_text())
    except frontmatter.FrontmatterError as e:
        raise BacklogError(f"{path} has {e}.") from e
    if lines is None:
        raise BacklogError(f"{path} has no frontmatter.")
    return lines, body


def read_task(path: Path) -> tuple[dict, str]:
    """A backlog task file's frontmatter and body."""
    lines, body = _frontmatter(path)
    try:
        return frontmatter.load(lines), body
    except frontmatter.FrontmatterError as e:
        raise BacklogError(f"{path} has {e}.") from e


def read_references(path: Path) -> list[str]:
    """The task's references list (empty if it has none)."""
    return [str(ref) for ref in read_task(path)[0].get("references") or []]


def set_parent_task(path: Path, todoist_id: str) -> list[str]:
    """Make `todoist_id` the task's only Todoist reference, keeping other references.

    Returns the task's new references list.
    """
    others = [ref for ref in read_references(path) if todoist_task_id(ref) is None]
    references = [*others, todoist_task_url(todoist_id)]
    lines, body = _frontmatter(path)
    path.write_text(frontmatter.join(frontmatter.set_list(lines, "references", references), body))
    return references
