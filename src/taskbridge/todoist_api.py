"""Todoist API client for TaskBridge."""

import logging
from dataclasses import dataclass, field
from typing import Any

import requests

from .config import config as config_manager


@dataclass
class TodoistProject:
    """Todoist project data structure."""

    id: str
    name: str
    color: str
    parent_id: str | None = None
    order: int = 0
    comment_count: int = 0
    is_shared: bool = False
    is_favorite: bool = False
    is_inbox_project: bool = False
    is_team_inbox: bool = False
    view_style: str = "list"
    url: str = ""


@dataclass
class TodoistTask:
    """Todoist task data structure."""

    id: str
    content: str
    description: str
    project_id: str
    section_id: str | None = None
    parent_id: str | None = None
    order: int = 0
    labels: list[str] = field(default_factory=lambda: [])
    priority: int = 1
    due: dict[str, Any] | None = None
    url: str = ""
    comment_count: int = 0
    created_at: str = ""
    creator_id: str = ""
    assignee_id: str | None = None
    assigner_id: str | None = None
    is_completed: bool = False

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.labels is None:
            self.labels = []


class TodoistAPI:
    """Todoist API client."""

    BASE_URL = "https://api.todoist.com/api/v1"

    def __init__(self, token: str | None = None):
        self.token = token or config_manager.get_todoist_token()
        if not self.token:
            raise ValueError("Todoist API token is required")

        self.session = requests.Session()
        # Todoist uses Bearer token authentication
        self.session.headers.update(
            {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        )

        self.logger = logging.getLogger(__name__)

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make a request to the Todoist API with exponential backoff."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"

        # Set a reasonable timeout if not provided (10 seconds for connect, 30 for read)
        if "timeout" not in kwargs:
            kwargs["timeout"] = (10, 30)

        try:
            self.logger.debug(f"Making {method} request to {url}")
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            # Handle empty responses (e.g., from DELETE requests or 204 status)
            if response.status_code == 204 or not response.content:
                return None

            return response.json()

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error: {e}")
            self.logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise
        except ValueError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            raise

    def _get_paginated(self, endpoint: str, params: dict | None = None) -> list[Any]:
        """Fetch all pages from a paginated list endpoint.

        API v1 list endpoints return {"results": [...], "next_cursor": "..."}.
        """
        params = dict(params or {})
        all_results: list[Any] = []

        while True:
            data = self._make_request("GET", endpoint, params=params)
            if data is None:
                break
            all_results.extend(data.get("results", []))
            cursor = data.get("next_cursor")
            if not cursor:
                break
            params["cursor"] = cursor

        return all_results

    def validate_token(self, token: str | None = None) -> bool:
        """Validate Todoist API token."""
        test_token = token or self.token
        try:
            headers = {"Authorization": f"Bearer {test_token}"}
            response = requests.get(f"{self.BASE_URL}/projects", headers=headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Token validation failed: {e}")
            return False

    def get_projects(self) -> list[TodoistProject]:
        """Get all projects."""
        try:
            data = self._get_paginated("/projects")
            projects = []
            for project_data in data:
                projects.append(
                    TodoistProject(
                        id=project_data["id"],
                        name=project_data["name"],
                        color=project_data.get("color", ""),
                        parent_id=project_data.get("parent_id"),
                        order=project_data.get("order", 0),
                        comment_count=project_data.get("comment_count", 0),
                        is_shared=project_data.get("is_shared", False),
                        is_favorite=project_data.get("is_favorite", False),
                        is_inbox_project=project_data.get("is_inbox_project", False),
                        is_team_inbox=project_data.get("is_team_inbox", False),
                        view_style=project_data.get("view_style", "list"),
                        url=project_data.get("url", ""),
                    )
                )
            return projects
        except Exception as e:
            self.logger.error(f"Failed to get projects: {e}")
            raise

    def get_project(self, project_id: str) -> TodoistProject | None:
        """Get a specific project by ID."""
        try:
            data = self._make_request("GET", f"/projects/{project_id}")
            if not data:
                return None

            return TodoistProject(
                id=data["id"],
                name=data["name"],
                color=data.get("color", ""),
                parent_id=data.get("parent_id"),
                order=data.get("order", 0),
                comment_count=data.get("comment_count", 0),
                is_shared=data.get("is_shared", False),
                is_favorite=data.get("is_favorite", False),
                is_inbox_project=data.get("is_inbox_project", False),
                is_team_inbox=data.get("is_team_inbox", False),
                view_style=data.get("view_style", "list"),
                url=data.get("url", ""),
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            self.logger.error(f"Failed to get project {project_id}: {e}")
            raise

    def create_project(
        self,
        name: str,
        color: str | None = None,
        parent_id: str | None = None,
        is_favorite: bool = False,
    ) -> TodoistProject:
        """Create a new project."""
        try:
            payload = {"name": name}
            if color:
                payload["color"] = color
            if parent_id:
                payload["parent_id"] = parent_id
            if is_favorite:
                payload["is_favorite"] = is_favorite

            data = self._make_request("POST", "/projects", json=payload)

            return TodoistProject(
                id=data["id"],
                name=data["name"],
                color=data.get("color", ""),
                parent_id=data.get("parent_id"),
                order=data.get("order", 0),
                comment_count=data.get("comment_count", 0),
                is_shared=data.get("is_shared", False),
                is_favorite=data.get("is_favorite", False),
                is_inbox_project=data.get("is_inbox_project", False),
                is_team_inbox=data.get("is_team_inbox", False),
                view_style=data.get("view_style", "list"),
                url=data.get("url", ""),
            )
        except Exception as e:
            self.logger.error(f"Failed to create project '{name}': {e}")
            raise

    def get_tasks(
        self,
        project_id: str | None = None,
        label: str | None = None,
        filter_query: str | None = None,
    ) -> list[TodoistTask]:
        """Get tasks with optional filtering.

        filter_query uses Todoist's filter language and routes to /tasks/filter.
        """
        try:
            if filter_query:
                # Filter queries use a dedicated endpoint in API v1
                data = self._get_paginated("/tasks/filter", {"query": filter_query})
            else:
                params: dict[str, Any] = {}
                if project_id:
                    params["project_id"] = project_id
                if label:
                    params["label"] = label
                data = self._get_paginated("/tasks", params)
            tasks = []

            for task_data in data:
                tasks.append(
                    TodoistTask(
                        id=task_data["id"],
                        content=task_data["content"],
                        description=task_data.get("description", ""),
                        project_id=task_data["project_id"],
                        section_id=task_data.get("section_id"),
                        parent_id=task_data.get("parent_id"),
                        order=task_data.get("order", 0),
                        labels=task_data.get("labels", []),
                        priority=task_data.get("priority", 1),
                        due=task_data.get("due"),
                        url=task_data.get("url", ""),
                        comment_count=task_data.get("comment_count", 0),
                        created_at=task_data.get("created_at", ""),
                        creator_id=task_data.get("creator_id", ""),
                        assignee_id=task_data.get("assignee_id"),
                        assigner_id=task_data.get("assigner_id"),
                        is_completed=task_data.get("is_completed", False),
                    )
                )

            return tasks
        except Exception as e:
            self.logger.error(f"Failed to get tasks: {e}")
            raise

    def get_task(self, task_id: str) -> TodoistTask | None:
        """Get a specific task by ID."""
        try:
            data = self._make_request("GET", f"/tasks/{task_id}")
            if not data:
                return None

            return TodoistTask(
                id=data["id"],
                content=data["content"],
                description=data.get("description", ""),
                project_id=data["project_id"],
                section_id=data.get("section_id"),
                parent_id=data.get("parent_id"),
                order=data.get("order", 0),
                labels=data.get("labels", []),
                priority=data.get("priority", 1),
                due=data.get("due"),
                url=data.get("url", ""),
                comment_count=data.get("comment_count", 0),
                created_at=data.get("created_at", ""),
                creator_id=data.get("creator_id", ""),
                assignee_id=data.get("assignee_id"),
                assigner_id=data.get("assigner_id"),
                is_completed=data.get("is_completed", False),
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            self.logger.error(f"Failed to get task {task_id}: {e}")
            raise

    def create_comment(self, task_id: str, content: str) -> bool:
        """Create a comment on a task."""
        try:
            payload = {"task_id": task_id, "content": content}
            self._make_request("POST", "/comments", json=payload)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create comment on task {task_id}: {e}")
            return False

    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update a task with the provided fields."""
        try:
            # Only include fields that are provided
            allowed_fields = {
                "content",
                "description",
                "labels",
                "priority",
                "due_string",
                "due_date",
                "due_datetime",
                "assignee_id",
            }
            payload = {k: v for k, v in kwargs.items() if k in allowed_fields}

            if not payload:
                self.logger.warning("No valid fields provided for task update")
                return False

            self._make_request("POST", f"/tasks/{task_id}", json=payload)
            return True
        except Exception as e:
            self.logger.error(f"Failed to update task {task_id}: {e}")
            return False

    def close_task(self, task_id: str) -> bool:
        """Close/complete a task."""
        try:
            self._make_request("POST", f"/tasks/{task_id}/close")
            return True
        except Exception as e:
            self.logger.error(f"Failed to close task {task_id}: {e}")
            return False

    def update_project(self, project_id: str, **kwargs) -> bool:
        """Update a project with the provided fields."""
        try:
            # Only include fields that are provided
            allowed_fields = {
                "name",
                "color",
                "is_favorite",
            }
            payload = {k: v for k, v in kwargs.items() if k in allowed_fields}

            if not payload:
                self.logger.warning("No valid fields provided for project update")
                return False

            self._make_request("POST", f"/projects/{project_id}", json=payload)
            return True
        except Exception as e:
            self.logger.error(f"Failed to update project {project_id}: {e}")
            return False

    def archive_project(self, project_id: str) -> bool:
        """Archive a project."""
        try:
            self._make_request("DELETE", f"/projects/{project_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to archive project {project_id}: {e}")
            return False
