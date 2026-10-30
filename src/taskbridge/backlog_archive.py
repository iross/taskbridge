"""Archive backlog.md tasks into their parent Todoist task's Obsidian note (ADR-004).

Each archived task becomes one section of the parent note, wrapped in begin/end
marker comments keyed by `<repo>/<TASK-ID>` so re-runs can find it again.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from . import backlog, frontmatter, task_notes
from .config import config as config_manager
from .database import db
from .provenance import RepoHistory
from .todoist_api import TodoistAPI

PROJECTS_DIR = "10 Projects"
ARCHIVE_DIR = "40 Archive"

_MARKER_RE = re.compile(r"^<!-- (?:SECTION:[A-Z_]+|AC|DOD):(?:BEGIN|END) -->$")
_AC_INDEX_RE = re.compile(r"^(- \[[ xX]\] )#\d+ ")
_HEADING_RE = re.compile(r"^#{1,5} ")
_TAG_UNSAFE_RE = re.compile(r"[^\w/-]")


class ArchiveError(Exception):
    """One task could not be archived; the message says why."""


@dataclass
class BacklogTask:
    """The parts of a backlog task file that go into the archived section."""

    id: str
    title: str
    status: str
    created: str
    updated: str
    labels: list[str]
    references: list[str]
    sections: list[tuple[str, str]]


@dataclass
class Outcome:
    """What archiving one task did (or, in a dry run, would do)."""

    action: str
    note: Path | None = None


def _date(value: object) -> str:
    return str(value or "")[:10]


def _sections(body: str) -> list[tuple[str, str]]:
    """(heading, markdown) for each `## ` section, cleaned for the parent note.

    Backlog marker comments and acceptance-criteria indexes are dropped, and
    headings inside a section are demoted one level; fenced code is left alone.
    """
    sections: list[tuple[str, list[str]]] = []
    in_fence = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            if line.startswith("## "):
                sections.append((line[3:].strip(), []))
                continue
            if _MARKER_RE.match(line.strip()):
                continue
            line = _AC_INDEX_RE.sub(r"\1", line)
            if _HEADING_RE.match(line):
                line = "#" + line
        if sections:
            sections[-1][1].append(line)
    cleaned = [(heading, "\n".join(lines).strip()) for heading, lines in sections]
    return [(heading, text) for heading, text in cleaned if text]


def parse_task(path: Path) -> BacklogTask:
    """Read a backlog task file."""
    meta, body = backlog.read_task(path)
    return BacklogTask(
        id=str(meta.get("id") or path.name.split(" ", 1)[0]).upper(),
        title=str(meta.get("title", "")),
        status=str(meta.get("status", "")),
        created=_date(meta.get("created_date")),
        updated=_date(meta.get("updated_date")),
        labels=[str(label) for label in meta.get("labels") or []],
        references=[str(ref) for ref in meta.get("references") or []],
        sections=_sections(body),
    )


def select_tasks(repo: Path, ids: list[str], done: bool) -> list[Path]:
    """Task files named by `ids`, or with `done`, every task whose status is Done."""
    if done:
        paths = [path for path in backlog.task_files(repo) if parse_task(path).status == "Done"]
        return sorted(paths, key=backlog.task_number)
    paths = [backlog.find_task_file(repo, task_id) for task_id in ids]
    return list(dict.fromkeys(paths))


def parent_id(task: BacklogTask) -> str | None:
    """The Todoist task this backlog task is linked to, or None if it is unlinked."""
    ids = {backlog.todoist_task_id(ref) for ref in task.references} - {None}
    if len(ids) > 1:
        raise ArchiveError(
            f"references {len(ids)} Todoist tasks; keep one with taskbridge backlog link"
        )
    return ids.pop() if ids else None


def section_key(repo_name: str, task: BacklogTask) -> str:
    """The `<repo>/<ID>` key used in markers and the note's backlog_tasks list."""
    return f"{repo_name}/{task.id}"


def render_section(task: BacklogTask, repo_name: str, provenance: str | None = None) -> str:
    """The markdown appended to the parent note for one task."""
    key = section_key(repo_name, task)
    details = [task.status or "no status"]
    if task.created:
        details.append(f"created {task.created}")
    if task.updated:
        details.append(f"updated {task.updated}")
    if task.labels:
        details.append("labels: " + ", ".join(task.labels))
    parts = [f"<!-- backlog:{key} -->", f"## {repo_name} {task.id} — {task.title}", ""]
    parts.append(" · ".join(details))
    for heading, text in task.sections:
        parts += ["", f"### {heading}", "", text]
    if provenance:
        parts += ["", "### Provenance", "", provenance]
    parts += ["", f"<!-- /backlog:{key} -->"]
    return "\n".join(parts) + "\n"


def _section_span(body: str, key: str) -> tuple[int, int] | None:
    """Start and end offsets of the task's section in a note body, if present."""
    begin, end = f"<!-- backlog:{key} -->", f"<!-- /backlog:{key} -->"
    start = body.find(begin)
    if start < 0:
        return None
    stop = body.find(end, start)
    if stop < 0:
        raise ArchiveError(f"the note has the start of {key}'s section but not its end marker")
    stop += len(end)
    return start, stop + 1 if body[stop : stop + 1] == "\n" else stop


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _with_archive_metadata(lines: list[str], key: str, repo_name: str) -> list[str]:
    """Frontmatter lines listing `key` in backlog_tasks and carrying the backlog tags."""
    data = frontmatter.load(lines)
    tasks = _as_list(data.get("backlog_tasks"))
    if key not in tasks:
        lines = frontmatter.set_list(lines, "backlog_tasks", [*tasks, key])
    tags = _as_list(data.get("tags"))
    wanted = ["backlog", "backlog/" + _TAG_UNSAFE_RE.sub("-", repo_name)]
    missing = [tag for tag in wanted if tag not in tags]
    if missing:
        lines = frontmatter.set_list(lines, "tags", [*tags, *missing])
    return lines


def has_section(note: Path, key: str) -> bool:
    """Whether the note already holds the task's section."""
    try:
        _, body = frontmatter.split(note.read_text())
    except frontmatter.FrontmatterError as e:
        raise ArchiveError(f"{note} has {e}") from e
    return _section_span(body, key) is not None


def archive_into_note(
    note: Path, task: BacklogTask, repo_name: str, force: bool, provenance: str | None = None
) -> str:
    """Append (or with `force`, replace) the task's section in the note.

    Returns "added", "replaced", or "exists" when the section is already there
    and `force` is off (the note is then left untouched).
    """
    key = section_key(repo_name, task)
    try:
        lines, body = frontmatter.split(note.read_text())
        span = _section_span(body, key)
        if span and not force:
            return "exists"
        section = render_section(task, repo_name, provenance)
        if span:
            body = body[: span[0]] + section + body[span[1] :]
        else:
            body = (body.rstrip("\n") + "\n\n" if body.strip() else "") + section
        lines = _with_archive_metadata(lines or [], key, repo_name)
    except frontmatter.FrontmatterError as e:
        raise ArchiveError(f"{note} has {e}") from e
    note.write_text(frontmatter.join(lines, body))
    return "replaced" if span else "added"


def locate_note(note_path: str, vault: Path) -> Path | None:
    """The note at its mapped path, or under 40 Archive/ if its project was archived."""
    path = Path(note_path)
    if path.exists():
        return path
    try:
        relative = path.relative_to(vault / PROJECTS_DIR)
    except ValueError:
        return None
    archived = vault / ARCHIVE_DIR / relative
    return archived if archived.exists() else None


def _parent_note(parent: str, api: TodoistAPI, vault: Path, dry_run: bool) -> tuple[Path, bool]:
    """The parent's note path and whether it exists yet; creates it unless `dry_run`."""
    mapping = db.get_todoist_note_by_task_id(parent)
    if mapping:
        note = locate_note(mapping.note_path, vault)
        if note is None:
            raise ArchiveError(
                f"parent {parent}'s note is missing from {mapping.note_path} and "
                f"{ARCHIVE_DIR}/; fix the mapping with taskbridge map update"
            )
        return note, True
    if dry_run:
        todoist_task = api.get_task(parent)
        if todoist_task is None:
            raise ArchiveError(f"parent Todoist task {parent} not found and has no note")
        project_name, _ = task_notes.resolve_project_info(todoist_task.project_id, api)
        return config_manager.task_note_path(project_name, todoist_task.content), False
    try:
        mapping, _ = task_notes.get_or_create_task_note(parent, api)
    except task_notes.TaskNotFoundError:
        raise ArchiveError(
            f"parent Todoist task {parent} not found (completed or deleted?) and has no note"
        ) from None
    return Path(mapping.note_path), True


def archive_task(
    path: Path,
    repo_name: str,
    api: TodoistAPI,
    *,
    dry_run: bool,
    force: bool,
    history: RepoHistory | None = None,
) -> Outcome:
    """Archive one backlog task file into its parent's note.

    Raises:
        ArchiveError: the task cannot be archived (bad link, missing parent, broken note).
    """
    task = parse_task(path)
    parent = parent_id(task)
    if parent is None:
        return Outcome("unlinked")
    vault = Path(config_manager.get_obsidian_vault_path()).expanduser()
    note, exists = _parent_note(parent, api, vault, dry_run)
    if not dry_run:
        provenance = history.markdown(task.id) if history else None
        return Outcome(archive_into_note(note, task, repo_name, force, provenance), note)
    if not exists:
        return Outcome("would create note and add", note)
    if has_section(note, section_key(repo_name, task)):
        return Outcome("would replace" if force else "exists", note)
    return Outcome("would add", note)
