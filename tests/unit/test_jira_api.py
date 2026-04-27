"""Unit tests for Jira API client."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from taskbridge.jira_api import JiraAPI, JiraIssue


@pytest.fixture
def jira():
    return JiraAPI(
        base_url="https://company.atlassian.net",
        email="user@example.com",
        api_token="test-token",
    )


def _search_response(issues: list[dict], total: int | None = None) -> dict:
    return {"issues": issues, "total": total if total is not None else len(issues), "startAt": 0}


def _issue(key: str = "PROJ-1", summary: str = "Fix bug") -> dict:
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "status": {"name": "In Progress"},
            "priority": {"name": "Medium"},
            "project": {"key": "PROJ", "name": "My Project"},
        },
    }


class TestJiraAPIInit:
    def test_trailing_slash_stripped(self):
        api = JiraAPI("https://company.atlassian.net/", "u@e.com", "tok")
        assert api.base_url == "https://company.atlassian.net"

    def test_session_auth_set(self):
        api = JiraAPI("https://company.atlassian.net", "u@e.com", "tok")
        assert api._session.auth == ("u@e.com", "tok")


class TestValidateCredentials:
    def test_returns_true_on_200(self, jira):
        mock_resp = MagicMock(status_code=200)
        with patch.object(jira._session, "get", return_value=mock_resp):
            assert jira.validate_credentials() is True

    def test_returns_false_on_401(self, jira):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=MagicMock(status_code=401)
        )
        with patch.object(jira._session, "get", return_value=mock_resp):
            assert jira.validate_credentials() is False

    def test_returns_false_on_network_error(self, jira):
        with patch.object(
            jira._session, "get", side_effect=requests.exceptions.ConnectionError("down")
        ):
            assert jira.validate_credentials() is False


class TestGetAssignedIssues:
    def test_returns_mapped_issues(self, jira):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = _search_response([_issue("PROJ-1", "Fix bug")])

        with patch.object(jira._session, "get", return_value=resp):
            issues = jira.get_assigned_issues()

        assert len(issues) == 1
        issue = issues[0]
        assert isinstance(issue, JiraIssue)
        assert issue.key == "PROJ-1"
        assert issue.summary == "Fix bug"
        assert issue.status == "In Progress"
        assert issue.priority == "Medium"
        assert issue.project_key == "PROJ"
        assert issue.project_name == "My Project"
        assert issue.url == "https://company.atlassian.net/browse/PROJ-1"

    def test_empty_results(self, jira):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = _search_response([])

        with patch.object(jira._session, "get", return_value=resp):
            assert jira.get_assigned_issues() == []

    def test_project_key_filter_injected_into_jql(self, jira):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = _search_response([])

        with patch.object(jira._session, "get", return_value=resp) as mock_get:
            jira.get_assigned_issues(project_keys=["PROJ", "OPS"])

        call_params = mock_get.call_args[1]["params"]
        assert "PROJ" in call_params["jql"]
        assert "OPS" in call_params["jql"]

    def test_pagination_fetches_all_pages(self, jira):
        page1 = {
            "issues": [_issue("PROJ-1")],
            "total": 2,
            "startAt": 0,
        }
        page2 = {
            "issues": [_issue("PROJ-2")],
            "total": 2,
            "startAt": 1,
        }

        responses = [MagicMock(), MagicMock()]
        responses[0].raise_for_status.return_value = None
        responses[0].json.return_value = page1
        responses[1].raise_for_status.return_value = None
        responses[1].json.return_value = page2

        with patch.object(jira._session, "get", side_effect=responses):
            issues = jira.get_assigned_issues()

        assert len(issues) == 2
        assert {i.key for i in issues} == {"PROJ-1", "PROJ-2"}

    def test_http_error_propagates(self, jira):
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError("403")

        with (
            patch.object(jira._session, "get", return_value=resp),
            pytest.raises(requests.exceptions.HTTPError),
        ):
            jira.get_assigned_issues()
