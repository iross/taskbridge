"""Toggl API client for TaskBridge."""

import requests
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from .config import config as config_manager


@dataclass
class TogglClient:
    """Toggl client data structure."""
    id: int
    name: str
    wid: int  # workspace id
    archived: bool = False
    server_deleted_at: Optional[str] = None


@dataclass
class TogglProject:
    """Toggl project data structure."""
    id: int
    name: str
    wid: int  # workspace id
    cid: Optional[int] = None  # client id
    active: bool = True
    is_private: bool = True
    template: bool = False
    template_id: Optional[int] = None
    billable: Optional[bool] = None
    auto_estimates: Optional[bool] = None
    estimated_hours: Optional[int] = None
    rate: Optional[float] = None
    color: str = "0"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class TogglTimeEntry:
    """Toggl time entry data structure."""
    id: Optional[int] = None
    description: str = ""
    wid: int = 0
    pid: Optional[int] = None  # project id
    tid: Optional[int] = None  # task id
    uid: int = 0  # user id
    created_with: str = "taskbridge"
    start: Optional[str] = None
    stop: Optional[str] = None
    duration: int = 0
    duronly: bool = False
    at: Optional[str] = None
    billable: bool = False


class TogglAPI:
    """Toggl API client."""
    
    BASE_URL = "https://api.track.toggl.com/api/v9"
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or config_manager.get_toggl_token()
        if not self.token:
            raise ValueError("Toggl API token is required")
        
        self.session = requests.Session()
        # Toggl uses HTTP Basic Auth with token:api_token
        self.session.auth = (self.token, 'api_token')
        self.session.headers.update({'Content-Type': 'application/json'})
        
        self.logger = logging.getLogger(__name__)
        self.workspace_id = None
        self._get_workspace_id()
    
    def _get_workspace_id(self) -> None:
        """Get the default workspace ID."""
        try:
            data = self._make_request('GET', '/me')
            self.workspace_id = data['default_workspace_id']
        except Exception as e:
            self.logger.error(f"Failed to get workspace ID: {e}")
            raise
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the Toggl API."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error {response.status_code}: {response.text}")
            raise Exception(f"Toggl API error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {e}")
            raise Exception(f"Toggl API request failed: {e}")
    
    def get_clients(self) -> List[TogglClient]:
        """Get all Toggl clients for the workspace."""
        if not self.workspace_id:
            return []
        
        data = self._make_request('GET', f'/workspaces/{self.workspace_id}/clients')
        
        clients = []
        for client_data in data:
            clients.append(TogglClient(
                id=client_data['id'],
                name=client_data['name'],
                wid=client_data['wid'],
                archived=client_data.get('archived', False),
                server_deleted_at=client_data.get('server_deleted_at')
            ))
        
        return clients
    
    def create_client(self, name: str) -> TogglClient:
        """Create a new Toggl client."""
        if not self.workspace_id:
            raise Exception("No workspace ID available")
        
        data = {'name': name}
        response_data = self._make_request('POST', f'/workspaces/{self.workspace_id}/clients', json=data)
        
        return TogglClient(
            id=response_data['id'],
            name=response_data['name'],
            wid=response_data['wid'],
            archived=response_data.get('archived', False),
            server_deleted_at=response_data.get('server_deleted_at')
        )
    
    def get_projects(self, client_id: Optional[int] = None) -> List[TogglProject]:
        """Get Toggl projects, optionally filtered by client."""
        if not self.workspace_id:
            return []
        
        data = self._make_request('GET', f'/workspaces/{self.workspace_id}/projects')
        
        projects = []
        for project_data in data:
            # Filter by client_id if specified
            if client_id is not None and project_data.get('cid') != client_id:
                continue
            
            projects.append(TogglProject(
                id=project_data['id'],
                name=project_data['name'],
                wid=project_data['wid'],
                cid=project_data.get('cid'),
                active=project_data.get('active', True),
                is_private=project_data.get('is_private', True),
                template=project_data.get('template', False),
                template_id=project_data.get('template_id'),
                billable=project_data.get('billable'),
                auto_estimates=project_data.get('auto_estimates'),
                estimated_hours=project_data.get('estimated_hours'),
                rate=project_data.get('rate'),
                color=project_data.get('color', '0'),
                created_at=project_data.get('created_at'),
                updated_at=project_data.get('updated_at')
            ))
        
        return projects
    
    def create_project(self, name: str, client_id: Optional[int] = None) -> TogglProject:
        """Create a new Toggl project."""
        if not self.workspace_id:
            raise Exception("No workspace ID available")
        
        data = {
            'name': name,
            'is_private': True,
            'active': True  # Explicitly set as active
        }
        if client_id:
            data['cid'] = client_id
        
        response_data = self._make_request('POST', f'/workspaces/{self.workspace_id}/projects', json=data)
        
        return TogglProject(
            id=response_data['id'],
            name=response_data['name'],
            wid=response_data['wid'],
            cid=response_data.get('cid'),
            active=response_data.get('active', True),
            is_private=response_data.get('is_private', True),
            template=response_data.get('template', False),
            template_id=response_data.get('template_id'),
            billable=response_data.get('billable'),
            auto_estimates=response_data.get('auto_estimates'),
            estimated_hours=response_data.get('estimated_hours'),
            rate=response_data.get('rate'),
            color=response_data.get('color', '0'),
            created_at=response_data.get('created_at'),
            updated_at=response_data.get('updated_at')
        )
    
    def start_timer(self, project_id: Optional[int], description: str) -> TogglTimeEntry:
        """Start a new time entry."""
        if not self.workspace_id:
            raise Exception("No workspace ID available")
        
        # Stop current timer if running
        self.stop_timer()
        
        data = {
            'description': description,
            'wid': self.workspace_id,  # This was missing!
            'created_with': 'taskbridge',
            'start': datetime.utcnow().isoformat() + 'Z',
            'duration': -1 * int(datetime.utcnow().timestamp())  # Negative duration for running timer
        }
        
        # Only add project_id if provided (some timers don't have projects)
        if project_id:
            data['pid'] = project_id
            self.logger.debug(f"Creating timer with project ID: {project_id}")
        else:
            self.logger.debug("Creating timer without project ID")
        
        self.logger.debug(f"Timer data: {data}")
        response_data = self._make_request('POST', f'/workspaces/{self.workspace_id}/time_entries', json=data)
        
        return TogglTimeEntry(
            id=response_data['id'],
            description=response_data.get('description', ''),
            wid=response_data['wid'],
            pid=response_data.get('pid'),
            tid=response_data.get('tid'),
            uid=response_data['uid'],
            created_with=response_data.get('created_with', 'taskbridge'),
            start=response_data.get('start'),
            stop=response_data.get('stop'),
            duration=response_data.get('duration', 0),
            duronly=response_data.get('duronly', False),
            at=response_data.get('at'),
            billable=response_data.get('billable', False)
        )
    
    def stop_timer(self) -> Optional[TogglTimeEntry]:
        """Stop the current running timer."""
        current_timer = self.get_current_timer()
        if not current_timer:
            return None
        
        if not self.workspace_id:
            raise Exception("No workspace ID available")
        
        # Update the time entry to stop it
        data = {'stop': datetime.utcnow().isoformat() + 'Z'}
        
        response_data = self._make_request('PUT', f'/workspaces/{self.workspace_id}/time_entries/{current_timer.id}', json=data)
        
        return TogglTimeEntry(
            id=response_data['id'],
            description=response_data.get('description', ''),
            wid=response_data['wid'],
            pid=response_data.get('pid'),
            tid=response_data.get('tid'),
            uid=response_data['uid'],
            created_with=response_data.get('created_with', 'taskbridge'),
            start=response_data.get('start'),
            stop=response_data.get('stop'),
            duration=response_data.get('duration', 0),
            duronly=response_data.get('duronly', False),
            at=response_data.get('at'),
            billable=response_data.get('billable', False)
        )
    
    def get_current_timer(self) -> Optional[TogglTimeEntry]:
        """Get the currently running timer."""
        try:
            data = self._make_request('GET', '/me/time_entries/current')
            
            if not data:
                return None
            
            return TogglTimeEntry(
                id=data['id'],
                description=data.get('description', ''),
                wid=data['wid'],
                pid=data.get('pid'),
                tid=data.get('tid'),
                uid=data['uid'],
                created_with=data.get('created_with', ''),
                start=data.get('start'),
                stop=data.get('stop'),
                duration=data.get('duration', 0),
                duronly=data.get('duronly', False),
                at=data.get('at'),
                billable=data.get('billable', False)
            )
        except Exception:
            # No current timer running
            return None
    
    def get_time_entries(self, start_date: str, end_date: str, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get time entries for a date range, optionally filtered by project.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            project_id: Optional project ID to filter by
            
        Returns:
            List of time entry dictionaries
        """
        if not self.workspace_id:
            return []
        
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        try:
            data = self._make_request('GET', f'/me/time_entries', params=params)
            
            # Filter by project if specified
            if project_id is not None:
                data = [entry for entry in data if entry.get('pid') == project_id]
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error fetching time entries: {e}")
            return []


# Global API instance (will be None if token not configured)
try:
    toggl_api = TogglAPI()
except ValueError:
    toggl_api = None