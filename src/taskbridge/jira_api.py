"""Jira Cloud REST API v3 client for TaskBridge."""

import logging
from dataclasses import dataclass

import requests


@dataclass
class JiraIssue:
    """A Jira issue assigned to the current user."""

    key: str
    summary: str
    status: str
    priority: str
    project_key: str
    project_name: str
    url: str


class JiraAPI:
    """Jira Cloud REST API v3 client using Basic Auth (email + API token)."""

    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.logger = logging.getLogger(__name__)
        self._session = requests.Session()
        self._session.auth = (email, api_token)
        self._session.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}/rest/api/3{path}"
        response = self._session.get(url, params=params, timeout=(10, 30))
        response.raise_for_status()
        return response.json()

    def validate_credentials(self) -> bool:
        """Return True if the configured credentials authenticate successfully."""
        try:
            self._get("/myself")
            return True
        except Exception:
            return False

    def get_assigned_issues(self, project_keys: list[str] | None = None) -> list[JiraIssue]:
        """Return all open issues assigned to the current user.

        Args:
            project_keys: Optional list of project keys to restrict the search.
        """
        jql = "assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC"
        if project_keys:
            key_list = ", ".join(project_keys)
            jql = f"project in ({key_list}) AND {jql}"

        issues: list[JiraIssue] = []
        start_at = 0
        max_results = 50

        while True:
            data = self._get(
                "/search",
                params={
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": "summary,status,priority,project",
                },
            )
            for item in data.get("issues", []):
                fields = item.get("fields", {})
                key = item["key"]
                issues.append(
                    JiraIssue(
                        key=key,
                        summary=fields.get("summary", ""),
                        status=fields.get("status", {}).get("name", ""),
                        priority=fields.get("priority", {}).get("name", ""),
                        project_key=fields.get("project", {}).get("key", ""),
                        project_name=fields.get("project", {}).get("name", ""),
                        url=f"{self.base_url}/browse/{key}",
                    )
                )
            total = data.get("total", 0)
            start_at += len(data.get("issues", []))
            if start_at >= total:
                break

        return issues
