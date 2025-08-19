"""Linear API client for TaskBridge."""

import requests
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .config import config as config_manager


@dataclass
class LinearProject:
    """Linear project data structure."""
    id: str
    name: str
    description: Optional[str] = None
    state: str = "planned"
    progress: float = 0.0
    target_date: Optional[str] = None
    lead_id: Optional[str] = None
    member_ids: List[str] = None
    team_id: str = ""
    url: str = ""
    labels: List[str] = None
    
    def __post_init__(self):
        if self.member_ids is None:
            self.member_ids = []
        if self.labels is None:
            self.labels = []


@dataclass
class LinearIssue:
    """Linear issue data structure."""
    id: str
    title: str
    description: Optional[str]
    project_id: Optional[str]
    state_id: str
    assignee_id: Optional[str] = None
    priority: int = 0
    estimate: Optional[float] = None
    labels: List[str] = None
    team_id: str = ""
    url: str = ""
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = []


class LinearAPI:
    """Linear API client using GraphQL."""
    
    BASE_URL = "https://api.linear.app/graphql"
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or config_manager.get_linear_token()
        if not self.token:
            raise ValueError("Linear API token is required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': self.token,
            'Content-Type': 'application/json'
        })
        
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GraphQL request to the Linear API."""
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        try:
            self.logger.debug(f"Making GraphQL request to {self.BASE_URL}")
            response = self.session.post(self.BASE_URL, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if 'errors' in data:
                error_messages = [error.get('message', 'Unknown error') for error in data['errors']]
                raise Exception(f"Linear API GraphQL errors: {'; '.join(error_messages)}")
            
            return data.get('data', {})
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error {response.status_code}: {response.text}")
            raise Exception(f"Linear API error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {e}")
            raise Exception(f"Linear API request failed: {e}")
    
    def get_projects(self) -> List[LinearProject]:
        """Get all Linear projects."""
        query = """
        query GetProjects {
            projects {
                nodes {
                    id
                    name
                    description
                    state
                    progress
                    targetDate
                    lead {
                        id
                    }
                    members {
                        nodes {
                            id
                        }
                    }
                    teams {
                        nodes {
                            id
                        }
                    }
                    url
                    labels {
                        nodes {
                            id
                            name
                            parent {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        
        data = self._make_request(query)
        projects = []
        
        for project_data in data.get('projects', {}).get('nodes', []):
            # Extract team_id from teams (assuming single team per project for simplicity)
            teams = project_data.get('teams', {}).get('nodes', [])
            team_id = teams[0]['id'] if teams else ""
            
            # Extract member IDs
            members = project_data.get('members', {}).get('nodes', [])
            member_ids = [member['id'] for member in members]
            
            # Extract labels with parent information
            labels_data = project_data.get('labels', {}).get('nodes', [])
            labels = []
            for label in labels_data:
                label_info = {
                    'id': label.get('id'),
                    'name': label.get('name'),
                    'parent': label.get('parent')
                }
                labels.append(label_info)
            
            projects.append(LinearProject(
                id=project_data['id'],
                name=project_data['name'],
                description=project_data.get('description'),
                state=project_data.get('state', 'planned'),
                progress=project_data.get('progress', 0.0),
                target_date=project_data.get('targetDate'),
                lead_id=project_data.get('lead', {}).get('id') if project_data.get('lead') else None,
                member_ids=member_ids,
                team_id=team_id,
                url=project_data.get('url', ''),
                labels=labels
            ))
        
        return projects
    
    def create_project(self, name: str, description: Optional[str] = None, team_id: Optional[str] = None) -> LinearProject:
        """Create a new Linear project."""
        query = """
        mutation CreateProject($input: ProjectCreateInput!) {
            projectCreate(input: $input) {
                project {
                    id
                    name
                    description
                    state
                    progress
                    targetDate
                    lead {
                        id
                    }
                    members {
                        nodes {
                            id
                        }
                    }
                    teams {
                        nodes {
                            id
                        }
                    }
                    url
                    labels {
                        nodes {
                            name
                        }
                    }
                }
                success
            }
        }
        """
        
        variables = {
            'input': {
                'name': name
            }
        }
        
        if description:
            variables['input']['description'] = description
        if team_id:
            variables['input']['teamIds'] = [team_id]
        
        data = self._make_request(query, variables)
        project_data = data.get('projectCreate', {}).get('project', {})
        
        if not project_data:
            raise Exception("Failed to create Linear project")
        
        # Parse the response similar to get_projects
        teams = project_data.get('teams', {}).get('nodes', [])
        team_id = teams[0]['id'] if teams else ""
        
        members = project_data.get('members', {}).get('nodes', [])
        member_ids = [member['id'] for member in members]
        
        labels_data = project_data.get('labels', {}).get('nodes', [])
        labels = [label['name'] for label in labels_data]
        
        return LinearProject(
            id=project_data['id'],
            name=project_data['name'],
            description=project_data.get('description'),
            state=project_data.get('state', 'planned'),
            progress=project_data.get('progress', 0.0),
            target_date=project_data.get('targetDate'),
            lead_id=project_data.get('lead', {}).get('id') if project_data.get('lead') else None,
            member_ids=member_ids,
            team_id=team_id,
            url=project_data.get('url', ''),
            labels=labels
        )
    
    def get_issues(self, project_id: Optional[str] = None, query: Optional[str] = None, limit: int = 50, include_done: bool = False) -> List[LinearIssue]:
        """Get Linear issues, optionally filtered by project or query.
        
        Args:
            project_id: Filter by specific project ID
            query: Search query for issue titles
            limit: Maximum number of issues to return
            include_done: Whether to include completed/canceled issues (default: False)
        """
        graphql_query = """
        query GetIssues($filter: IssueFilter, $first: Int, $orderBy: PaginationOrderBy) {
            issues(filter: $filter, first: $first, orderBy: $orderBy) {
                nodes {
                    id
                    title
                    description
                    project {
                        id
                        name
                    }
                    state {
                        id
                        name
                        type
                    }
                    assignee {
                        id
                        name
                    }
                    priority
                    estimate
                    labels {
                        nodes {
                            name
                        }
                    }
                    team {
                        id
                        name
                    }
                    url
                    createdAt
                    updatedAt
                }
            }
        }
        """
        
        variables = {
            'first': limit,
            'orderBy': 'updatedAt'  # Order by most recently updated for "recent" issues
        }
        filter_conditions = {}
        
        if project_id:
            filter_conditions['project'] = {'id': {'eq': project_id}}
        
        if query:
            filter_conditions['title'] = {'contains': query}
        
        # Filter out completed issues by default unless include_done is True
        if not include_done:
            # Get active issues (not completed/cancelled)
            filter_conditions['state'] = {'type': {'nin': ['completed', 'canceled']}}
        
        if filter_conditions:
            variables['filter'] = filter_conditions
        
        data = self._make_request(graphql_query, variables)
        issues = []
        
        for issue_data in data.get('issues', {}).get('nodes', []):
            # Extract label names
            labels_data = issue_data.get('labels', {}).get('nodes', [])
            labels = [label['name'] for label in labels_data]
            
            issues.append(LinearIssue(
                id=issue_data['id'],
                title=issue_data['title'],
                description=issue_data.get('description'),
                project_id=issue_data.get('project', {}).get('id') if issue_data.get('project') else None,
                state_id=issue_data.get('state', {}).get('id', ''),
                assignee_id=issue_data.get('assignee', {}).get('id') if issue_data.get('assignee') else None,
                priority=issue_data.get('priority', 0),
                estimate=issue_data.get('estimate'),
                labels=labels,
                team_id=issue_data.get('team', {}).get('id', ''),
                url=issue_data.get('url', ''),
                created_at=issue_data.get('createdAt', ''),
                updated_at=issue_data.get('updatedAt', '')
            ))
        
        return issues
    
    def get_recent_issues(self, limit: int = 10) -> List[LinearIssue]:
        """Get recent active issues, ordered by last update."""
        return self.get_issues(limit=limit)
    
    def get_issue_comments(self, issue_id: str) -> List[Dict[str, Any]]:
        """Get comments for a specific issue.
        
        Args:
            issue_id: The Linear issue ID
            
        Returns:
            List of comment dictionaries with body, createdAt, etc.
        """
        query = """
        query GetIssueComments($issueId: String!) {
            issue(id: $issueId) {
                comments {
                    nodes {
                        id
                        body
                        createdAt
                        user {
                            name
                        }
                    }
                }
            }
        }
        """
        
        try:
            data = self._make_request(query, {"issueId": issue_id})
            comments = data.get('issue', {}).get('comments', {}).get('nodes', [])
            return comments
        except Exception as e:
            self.logger.error(f"Error fetching comments for issue {issue_id}: {e}")
            return []
    
    def create_comment(self, issue_id: str, body: str) -> bool:
        """Create a comment on a Linear issue.
        
        Args:
            issue_id: The Linear issue ID
            body: The comment body text
            
        Returns:
            True if comment was created successfully, False otherwise
        """
        query = """
        mutation CreateComment($input: CommentCreateInput!) {
            commentCreate(input: $input) {
                success
                comment {
                    id
                    body
                }
            }
        }
        """
        
        variables = {
            'input': {
                'issueId': issue_id,
                'body': body
            }
        }
        
        try:
            result = self._make_request(query, variables)
            return result.get('commentCreate', {}).get('success', False)
        except Exception as e:
            self.logger.error(f"Failed to create comment on issue {issue_id}: {e}")
            return False
    
    def parse_client_project_name(self, labels: list) -> Tuple[Optional[str], Optional[str]]:
        """Parse client name from project labels.
        
        Recognizes two formats:
        1. #client/CLIENT_NAME format (legacy)
        2. Labels that have a parent named "client" (preferred)
        
        Args:
            labels: List of label objects with id, name, and parent information
        
        Returns:
            Tuple of (client_name, None) or (None, None) if no client found
            Note: The second value is None because Linear projects themselves represent the "project"
        """
        # Handle both old format (list of strings) and new format (list of dicts)
        if labels and isinstance(labels[0], str):
            # Legacy format - list of label names
            for label in labels:
                if label.startswith('#client/'):
                    client_part = label[8:]  # len('#client/') = 8
                    if client_part.strip():
                        return client_part.strip(), None
            return None, None
        
        # New format - list of label objects with parent info
        for label in labels:
            if isinstance(label, dict):
                label_name = label.get('name')
                parent = label.get('parent')
                
                # First try the #client/CLIENT_NAME format
                if label_name and label_name.startswith('#client/'):
                    client_part = label_name[8:]  # len('#client/') = 8
                    if client_part.strip():
                        return client_part.strip(), None
                
                # Check if this label has a parent named "client"
                if parent and parent.get('name') == 'client' and label_name:
                    return label_name, None
        
        return None, None
    
    def get_projects_with_parsed_names(self) -> List[Tuple[LinearProject, Optional[str], Optional[str]]]:
        """Get all projects with parsed client/project names.
        
        Returns:
            List of tuples: (project, client_name, project_name)
            project_name will be the project.name
            client_name will be extracted from #client/CLIENT_NAME labels or None
        """
        projects = self.get_projects()
        result = []
        
        for project in projects:
            client_name, _ = self.parse_client_project_name(project.labels)
            # Use the project name as the "project_name" part
            result.append((project, client_name, project.name))
        
        return result


# Global API instance (will be None if token not configured)
try:
    linear_api = LinearAPI()
except ValueError:
    linear_api = None