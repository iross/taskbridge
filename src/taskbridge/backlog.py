"""Links between backlog.md tasks and their parent Todoist task (ADR-004).

A backlog task names its parent with a Todoist task URL in its frontmatter
`references` list. The backlog CLI cannot edit tasks in `completed/`, so the
references block is rewritten here directly, in the format the CLI writes.
"""

import re
from pathlib import Path

import yaml

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


def find_task_file(repo: Path, task_id: str) -> Path:
    """Locate a backlog task's file in the repo's backlog/tasks or backlog/completed."""
    backlog_dir = repo / "backlog"
    if not backlog_dir.is_dir():
        raise BacklogError(f"No backlog/ directory in {repo.resolve()}. Pass --repo.")
    wanted = _normalize_task_id(task_id)
    for sub in _TASK_DIRS:
        for path in sorted((backlog_dir / sub).glob("task-*.md")):
            if _normalize_task_id(path.name.split(" ", 1)[0].removesuffix(".md")) == wanted:
                return path
    raise BacklogError(f"Backlog task {task_id} not found in {backlog_dir.resolve()}.")


def _split_frontmatter(text: str, path: Path) -> tuple[list[str], str]:
    """Frontmatter lines (without the --- fences) and the body after them."""
    if not text.startswith("---\n"):
        raise BacklogError(f"{path} has no frontmatter.")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise BacklogError(f"{path} has unterminated frontmatter.")
    return text[4:end].split("\n"), text[end + len("\n---\n") :]


def read_references(path: Path) -> list[str]:
    """The task's references list (empty if it has none)."""
    lines, _ = _split_frontmatter(path.read_text(), path)
    try:
        frontmatter = yaml.safe_load("\n".join(lines)) or {}
    except yaml.YAMLError as e:
        raise BacklogError(f"{path} has invalid frontmatter: {e}") from e
    return [str(ref) for ref in frontmatter.get("references") or []]


def _without_references(lines: list[str]) -> list[str]:
    """Frontmatter lines with the references key and its list items removed."""
    kept: list[str] = []
    in_references = False
    for line in lines:
        if line.startswith("references:"):
            in_references = True
            continue
        if in_references and line.startswith("  "):
            continue
        in_references = False
        kept.append(line)
    return kept


def set_parent_task(path: Path, todoist_id: str) -> list[str]:
    """Make `todoist_id` the task's only Todoist reference, keeping other references.

    Returns the task's new references list.
    """
    others = [ref for ref in read_references(path) if todoist_task_id(ref) is None]
    references = [*others, todoist_task_url(todoist_id)]
    lines, body = _split_frontmatter(path.read_text(), path)
    block = ["references:"] + ["  - '" + ref.replace("'", "''") + "'" for ref in references]
    path.write_text("---\n" + "\n".join(_without_references(lines) + block) + "\n---\n" + body)
    return references
