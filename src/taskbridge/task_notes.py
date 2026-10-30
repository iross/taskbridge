"""Obsidian notes for Todoist tasks: where they go and how they are created."""

import contextlib

from .config import config as config_manager
from .database import TodoistNoteMapping, db
from .todoist_api import TodoistAPI


class TaskNotFoundError(LookupError):
    """The Todoist task does not exist (or its ID is malformed)."""


def resolve_project_info(project_id: str, api: TodoistAPI) -> tuple[str, str]:
    """Return (project_name, client_name) for a Todoist project.

    Manual config mappings take precedence. Otherwise the top-level ancestor
    in the project hierarchy becomes the client and the direct project becomes
    the folder name.
    """
    manual = config_manager.get_todoist_project_mappings().get(project_id)
    if manual:
        return manual["folder"], manual.get("client", "")

    project = api.get_project(project_id)
    if not project:
        return "Unknown", ""

    if not project.parent_id:
        return project.name, ""

    # Walk up to the root ancestor — that becomes the client
    current = project
    client_name = project.name
    while current.parent_id:
        parent = api.get_project(current.parent_id)
        if not parent:
            break
        client_name = parent.name
        current = parent

    return project.name, client_name


def get_or_create_task_note(
    task_id: str, api: TodoistAPI | None = None
) -> tuple[TodoistNoteMapping, bool]:
    """Return (mapping, is_new) for the note mapped to a Todoist task.

    Creates the note, its Todoist mapping, and a linking task comment when no
    mapping exists yet; otherwise returns the existing mapping unchanged.

    Raises:
        TaskNotFoundError: no mapping exists and Todoist has no such task.
    """
    existing = db.get_todoist_note_by_task_id(task_id)
    if existing:
        return existing, False

    api = api or TodoistAPI()
    task = api.get_task(task_id)
    if not task:
        raise TaskNotFoundError(f"Task {task_id} not found in Todoist")

    project_name, client_name = resolve_project_info(task.project_id, api)
    note_path = config_manager.create_task_note(
        project_name=project_name,
        task_title=task.content,
        client=client_name,
        status="backlog",
        tags=task.labels,
    )
    mapping = TodoistNoteMapping(
        todoist_task_id=task_id,
        todoist_project_id=task.project_id,
        note_path=str(note_path),
        obsidian_url=config_manager.generate_obsidian_url(project_name, note_path.name),
    )
    db.create_todoist_note_mapping(mapping)

    with contextlib.suppress(Exception):
        api.create_comment(task_id, f"📝 Obsidian note: [Open Note]({mapping.obsidian_url})")

    return mapping, True
