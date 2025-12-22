"""Taskwarrior provider implementation following the provider schema."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .taskwarrior_api import TaskWarriorAPI, TaskWarriorTask


@dataclass
class UniversalIssue:
    """Universal issue model for cross-provider compatibility."""

    id: str  # Provider-specific ID
    title: str  # Issue title
    description: str | None  # Issue description
    state: str  # Normalized state (pending, completed, deleted)
    priority: str  # Normalized priority (H, M, L, or "")
    assignee_id: str | None  # Assignee identifier
    project_id: str | None  # Project identifier
    labels: list[str]  # Issue labels/tags
    estimate: str | None  # Time estimate
    url: str  # Direct link to issue (empty for Taskwarrior)
    created_at: str  # ISO timestamp
    updated_at: str  # ISO timestamp
    custom_fields: dict[str, Any]  # Provider-specific fields


@dataclass
class UniversalProject:
    """Universal project model for cross-provider compatibility."""

    id: str  # Provider-specific ID
    name: str  # Project name
    description: str | None  # Project description
    state: str  # Normalized state (active, completed, etc.)
    progress: float  # Progress percentage (0.0-1.0)
    labels: list[str]  # Project labels/tags
    url: str  # Direct link to project (empty for Taskwarrior)
    custom_fields: dict[str, Any]  # Provider-specific fields


class IssueProvider(ABC):
    """Abstract interface for issue tracking systems."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'linear', 'todoist', 'taskwarrior')."""
        pass

    @abstractmethod
    def authenticate(self, _credentials: dict[str, Any]) -> bool:
        """Authenticate with the provider using given credentials."""
        pass

    @abstractmethod
    def get_projects(self) -> list[UniversalProject]:
        """Retrieve all projects from the provider."""
        pass

    @abstractmethod
    def get_issues(
        self,
        project_id: str | None = None,
        query: str | None = None,
        limit: int = 50,
        include_done: bool = False,
    ) -> list[UniversalIssue]:
        """Retrieve issues, optionally filtered by project or search query."""
        pass

    @abstractmethod
    def create_comment(self, issue_id: str, body: str) -> bool:
        """Add a comment to an issue."""
        pass

    @abstractmethod
    def parse_client_project_name(self, project_or_labels: Any) -> tuple[str | None, str | None]:
        """Extract client and project names from provider-specific data."""
        pass


class TaskwarriorProvider(IssueProvider):
    """Taskwarrior implementation of the issue provider interface."""

    def __init__(self, task_cmd: str = "task"):
        """Initialize Taskwarrior provider.

        Args:
            task_cmd: Path to task command (default: "task")
        """
        self.api = TaskWarriorAPI(task_cmd)

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "taskwarrior"

    def authenticate(self, _credentials: dict[str, Any]) -> bool:
        """Authenticate with Taskwarrior.

        For Taskwarrior, authentication is just verifying the CLI is available.

        Args:
            credentials: Not used for Taskwarrior

        Returns:
            True if Taskwarrior is available
        """
        try:
            self.api._verify_taskwarrior()
            return True
        except ValueError:
            return False

    def get_projects(self) -> list[UniversalProject]:
        """Retrieve all projects from Taskwarrior."""
        tw_projects = self.api.get_projects()

        universal_projects = []
        for tw_project in tw_projects:
            # Calculate progress based on completed vs pending tasks
            progress = 0.0
            if tw_project.tasks_count > 0:
                progress = tw_project.completed_count / tw_project.tasks_count

            universal_projects.append(
                UniversalProject(
                    id=tw_project.name,  # Use project name as ID
                    name=tw_project.name,
                    description=tw_project.description,
                    state="active" if tw_project.pending_count > 0 else "completed",
                    progress=progress,
                    labels=[],  # Taskwarrior doesn't have project labels
                    url="",  # No URL for Taskwarrior
                    custom_fields={
                        "tasks_count": tw_project.tasks_count,
                        "pending_count": tw_project.pending_count,
                        "completed_count": tw_project.completed_count,
                    },
                )
            )

        return universal_projects

    def get_issues(
        self,
        project_id: str | None = None,
        query: str | None = None,
        limit: int = 50,
        include_done: bool = False,
    ) -> list[UniversalIssue]:
        """Retrieve issues from Taskwarrior.

        Args:
            project_id: Filter by project name
            query: Search query (matches description)
            limit: Maximum number of issues to return
            include_done: Whether to include completed/deleted tasks

        Returns:
            List of universal issues
        """
        # Get tasks based on filters
        if project_id:
            tasks = self.api.get_tasks_by_project(project_id)
        else:
            # Get pending tasks by default, or all tasks if include_done is True
            tasks = self.api.get_all_tasks() if include_done else self.api.get_pending_tasks()

        # Apply text search filter
        if query:
            query_lower = query.lower()
            tasks = [t for t in tasks if query_lower in t.description.lower()]

        # Apply limit
        if limit > 0:
            tasks = tasks[:limit]

        # Convert to universal issues
        universal_issues = []
        for task in tasks:
            universal_issues.append(self._task_to_universal_issue(task))

        return universal_issues

    def create_comment(self, issue_id: str, body: str) -> bool:
        """Add a comment (annotation) to a Taskwarrior task.

        Args:
            issue_id: Task UUID
            body: Comment text

        Returns:
            True if successful
        """
        return self.api.add_annotation(issue_id, body)

    def parse_client_project_name(self, project_or_labels: Any) -> tuple[str | None, str | None]:
        """Extract client and project names from Taskwarrior task data.

        For Taskwarrior, we look for tags that follow patterns like:
        - client:CLIENT_NAME
        - #client/CLIENT_NAME (similar to Linear)
        - Or use the project field directly

        Args:
            project_or_labels: TaskWarrior task or project name

        Returns:
            Tuple of (client_name, project_name)
        """
        client_name = None
        project_name = None

        # Handle TaskWarriorTask objects
        if isinstance(project_or_labels, TaskWarriorTask):
            task = project_or_labels
            project_name = task.project

            # Look for client tags
            if task.tags:
                for tag in task.tags:
                    # Look for client:NAME pattern
                    if tag.startswith("client:"):
                        client_name = tag[7:]  # Remove 'client:' prefix
                        break
                    # Look for #client/NAME pattern (Linear style)
                    elif tag.startswith("#client/"):
                        client_name = tag[8:]  # Remove '#client/' prefix
                        break

        # Handle string project names
        elif isinstance(project_or_labels, str):
            project_name = project_or_labels

            # Try to extract client from project name patterns like "ClientName_ProjectName"
            if "_" in project_name:
                parts = project_name.split("_", 1)
                if len(parts) == 2:
                    client_name, project_name = parts

        return client_name, project_name

    def _task_to_universal_issue(self, task: TaskWarriorTask) -> UniversalIssue:
        """Convert TaskWarrior task to universal issue format.

        Args:
            task: TaskWarrior task

        Returns:
            Universal issue
        """
        # Normalize state
        state_mapping = {
            "pending": "pending",
            "completed": "completed",
            "deleted": "deleted",
            "waiting": "pending",
            "recurring": "pending",
        }
        normalized_state = state_mapping.get(task.status, task.status)

        # Normalize priority
        priority_mapping = {"H": "H", "M": "M", "L": "L"}
        normalized_priority = priority_mapping.get(task.priority, "")

        return UniversalIssue(
            id=task.uuid,
            title=task.description,
            description=None,  # Taskwarrior doesn't have separate description field
            state=normalized_state,
            priority=normalized_priority,
            assignee_id=None,  # Taskwarrior doesn't have assignees
            project_id=task.project,
            labels=task.tags or [],
            estimate=task.estimate,
            url="",  # No URLs for Taskwarrior
            created_at=task.entry or "",
            updated_at=task.modified or "",
            custom_fields={
                "urgency": task.urgency,
                "annotations": task.annotations,
                **task.custom_fields,
            },
        )

    def create_issue(self, issue: UniversalIssue) -> str | None:
        """Create a new issue in Taskwarrior.

        Args:
            issue: Universal issue to create

        Returns:
            Created task UUID or None if failed
        """
        # Convert universal issue to TaskWarrior task
        task = TaskWarriorTask(
            uuid="",  # Will be generated
            description=issue.title,
            status="pending",
            project=issue.project_id,
            priority=issue.priority if issue.priority else None,
            tags=issue.labels,
            estimate=issue.estimate,
            annotations=issue.custom_fields.get("annotations", []) if issue.custom_fields else [],
        )

        try:
            created_task = self.api.create_task(task)

            # Add any additional annotations after creation
            if created_task and issue.custom_fields and "annotations" in issue.custom_fields:
                annotations = issue.custom_fields["annotations"]
                for annotation in annotations:
                    if isinstance(annotation, dict) and "description" in annotation:
                        self.api.add_annotation(created_task.uuid, annotation["description"])

            return created_task.uuid if created_task else None
        except Exception:
            return None

    def update_issue(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update an existing issue in Taskwarrior.

        Args:
            issue_id: Task UUID
            updates: Dictionary of fields to update

        Returns:
            True if successful
        """
        # Map universal field names to Taskwarrior field names
        tw_updates = {}

        if "title" in updates:
            tw_updates["description"] = updates["title"]
        if "project_id" in updates:
            tw_updates["project"] = updates["project_id"]
        if "priority" in updates:
            tw_updates["priority"] = updates["priority"]
        if "labels" in updates:
            tw_updates["tags"] = updates["labels"]
        if "estimate" in updates:
            tw_updates["estimate"] = updates["estimate"]

        return self.api.update_task(issue_id, tw_updates)

    def complete_issue(self, issue_id: str) -> bool:
        """Mark an issue as completed.

        Args:
            issue_id: Task UUID

        Returns:
            True if successful
        """
        return self.api.complete_task(issue_id)

    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue.

        Args:
            issue_id: Task UUID

        Returns:
            True if successful
        """
        return self.api.delete_task(issue_id)
