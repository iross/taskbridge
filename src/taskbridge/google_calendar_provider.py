"""Google Calendar provider implementation following the provider schema."""

import os
import json
import pickle
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .taskwarrior_provider import IssueProvider, UniversalIssue, UniversalProject


class GoogleCalendarProvider(IssueProvider):
    """Google Calendar implementation of the issue provider interface."""
    
    # Required scopes for Google Calendar API
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    
    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.pickle"):
        """Initialize Google Calendar provider.
        
        Args:
            credentials_file: Path to OAuth credentials JSON file
            token_file: Path to save/load access tokens
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._credentials = None
    
    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "google_calendar"
    
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with Google Calendar API.
        
        Args:
            credentials: Dictionary containing:
                - credentials_file: Path to OAuth credentials JSON (optional)
                - token_file: Path to token storage (optional)
                
        Returns:
            True if authentication successful
        """
        # Update paths if provided
        if 'credentials_file' in credentials:
            self.credentials_file = credentials['credentials_file']
        if 'token_file' in credentials:
            self.token_file = credentials['token_file']
        
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
            
            self._credentials = creds
            self.service = build('calendar', 'v3', credentials=creds)
            return True
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def get_projects(self) -> List[UniversalProject]:
        """Retrieve all calendars as projects from Google Calendar.
        
        Returns:
            List of calendars as UniversalProject objects
        """
        if not self.service:
            return []
        
        try:
            # Get calendar list
            calendars_result = self.service.calendarList().list().execute()
            calendars = calendars_result.get('items', [])
            
            projects = []
            for calendar in calendars:
                # Skip calendars we don't have access to or are hidden
                if calendar.get('accessRole') not in ['owner', 'writer', 'reader']:
                    continue
                
                projects.append(UniversalProject(
                    id=calendar['id'],
                    name=calendar.get('summary', 'Unknown Calendar'),
                    description=calendar.get('description', ''),
                    state="active",  # All calendars are considered active
                    progress=0.0,    # No meaningful progress for calendars
                    labels=[],       # No labels in Google Calendar
                    url=f"https://calendar.google.com/calendar/u/0/r/month/{calendar['id']}",
                    custom_fields={
                        'access_role': calendar.get('accessRole'),
                        'primary': calendar.get('primary', False),
                        'color_id': calendar.get('colorId'),
                        'background_color': calendar.get('backgroundColor'),
                        'foreground_color': calendar.get('foregroundColor')
                    }
                ))
            
            return projects
            
        except HttpError as e:
            print(f"Failed to get calendars: {e}")
            return []
    
    def get_issues(self, project_id: Optional[str] = None, 
                   query: Optional[str] = None, 
                   limit: int = 50,
                   include_done: bool = False) -> List[UniversalIssue]:
        """Retrieve calendar events as issues from Google Calendar.
        
        Args:
            project_id: Calendar ID to filter by (if None, uses primary calendar)
            query: Search query for event titles/descriptions
            limit: Maximum number of events to return
            include_done: Whether to include past events (completed)
            
        Returns:
            List of calendar events as UniversalIssue objects
        """
        if not self.service:
            return []
        
        try:
            # Use primary calendar if no project_id specified
            calendar_id = project_id if project_id else 'primary'
            
            # Set time bounds
            now = datetime.now(timezone.utc)
            if include_done:
                # Include events from last 30 days
                time_min = (now - timedelta(days=30)).isoformat()
            else:
                # Only future events
                time_min = now.isoformat()
            
            # Future events only (next 30 days to avoid too many results)
            time_max = (now + timedelta(days=30)).isoformat()
            
            # Build API request
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=limit,
                singleEvents=True,
                orderBy='startTime',
                q=query if query else None
            ).execute()
            
            events = events_result.get('items', [])
            
            # Convert events to UniversalIssue objects
            issues = []
            for event in events:
                issue = self._event_to_universal_issue(event, calendar_id)
                if issue:
                    issues.append(issue)
            
            return issues
            
        except HttpError as e:
            print(f"Failed to get events: {e}")
            return []
    
    def create_comment(self, issue_id: str, body: str) -> bool:
        """Add a comment to a calendar event.
        
        Google Calendar doesn't have comments, but we could add to description.
        This is not implemented as it would modify the original event.
        
        Args:
            issue_id: Event ID
            body: Comment text
            
        Returns:
            False (not implemented)
        """
        # Not implementing this as it would modify calendar events
        return False
    
    def parse_client_project_name(self, 
                                  project_or_labels: Any) -> Tuple[Optional[str], Optional[str]]:
        """Extract client and project names from calendar event data.
        
        For Google Calendar, we look for patterns in event titles or descriptions:
        - [ClientName] Event Title
        - ClientName: Event Title
        - #client/ClientName patterns in description
        
        Args:
            project_or_labels: Calendar event or calendar name
            
        Returns:
            Tuple of (client_name, project_name)
        """
        client_name = None
        project_name = None
        
        # Handle calendar event objects (from API)
        if isinstance(project_or_labels, dict) and 'summary' in project_or_labels:
            event = project_or_labels
            title = event.get('summary', '')
            description = event.get('description', '')
            
            # Look for [ClientName] pattern in title
            if title.startswith('[') and ']' in title:
                end_bracket = title.find(']')
                client_name = title[1:end_bracket]
                project_name = title[end_bracket+1:].strip()
            # Look for ClientName: pattern in title
            elif ':' in title:
                parts = title.split(':', 1)
                if len(parts) == 2:
                    client_name = parts[0].strip()
                    project_name = parts[1].strip()
            
            # Look for #client/ClientName in description
            if not client_name and description:
                import re
                client_match = re.search(r'#client/(\w+)', description)
                if client_match:
                    client_name = client_match.group(1)
        
        # Handle string calendar names
        elif isinstance(project_or_labels, str):
            calendar_name = project_or_labels
            project_name = calendar_name
            
            # Try to extract client from calendar name patterns
            if '_' in calendar_name:
                parts = calendar_name.split('_', 1)
                if len(parts) == 2:
                    client_name, project_name = parts
        
        return client_name, project_name
    
    def _event_to_universal_issue(self, event: Dict[str, Any], calendar_id: str) -> Optional[UniversalIssue]:
        """Convert Google Calendar event to UniversalIssue format.
        
        Args:
            event: Google Calendar event object
            calendar_id: Calendar ID this event belongs to
            
        Returns:
            UniversalIssue object or None if conversion fails
        """
        try:
            # Extract basic event info
            event_id = event.get('id', '')
            title = event.get('summary', 'Untitled Event')
            description = event.get('description', '')
            
            # Determine if event is in the past (completed)
            now = datetime.now(timezone.utc)
            start_time = event.get('start', {})
            
            # Handle both datetime and date events
            if 'dateTime' in start_time:
                start_dt = datetime.fromisoformat(start_time['dateTime'].replace('Z', '+00:00'))
                is_past = start_dt < now
            elif 'date' in start_time:
                # All-day events
                start_date = datetime.fromisoformat(start_time['date'] + 'T00:00:00+00:00')
                is_past = start_date.date() < now.date()
            else:
                is_past = False
            
            # Extract attendees info
            attendees = event.get('attendees', [])
            attendee_emails = [att.get('email', '') for att in attendees if att.get('email')]
            
            # Extract meeting duration for estimate
            end_time = event.get('end', {})
            duration_minutes = None
            if 'dateTime' in start_time and 'dateTime' in end_time:
                start_dt = datetime.fromisoformat(start_time['dateTime'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time['dateTime'].replace('Z', '+00:00'))
                duration = end_dt - start_dt
                duration_minutes = int(duration.total_seconds() / 60)
            
            # Build labels - always include _meeting tag as requested
            labels = ['_meeting']
            
            # Add calendar name as a label if it's not the primary calendar
            if calendar_id != 'primary':
                # Get calendar name for label
                try:
                    calendar_info = self.service.calendarList().get(calendarId=calendar_id).execute()
                    calendar_name = calendar_info.get('summary', '').replace(' ', '_').lower()
                    if calendar_name:
                        labels.append(f'calendar:{calendar_name}')
                except:
                    pass
            
            # Add meeting type labels based on attendee count
            if len(attendees) == 0:
                labels.append('solo')
            elif len(attendees) == 1:
                labels.append('1on1')
            else:
                labels.append('group')
            
            # Create meeting URL
            meeting_url = event.get('htmlLink', '')
            if event.get('hangoutLink'):
                meeting_url = event['hangoutLink']
            elif event.get('location') and 'meet.google.com' in event['location']:
                meeting_url = event['location']
            
            return UniversalIssue(
                id=event_id,
                title=title,
                description=description,
                state="completed" if is_past else "pending",
                priority="M",  # Default to medium priority for meetings
                assignee_id=None,  # Calendar events don't have assignees
                project_id=calendar_id,
                labels=labels,
                estimate=f"{duration_minutes}min" if duration_minutes else None,
                url=meeting_url,
                created_at=event.get('created', ''),
                updated_at=event.get('updated', ''),
                custom_fields={
                    'start_time': start_time,
                    'end_time': end_time,
                    'attendees': attendee_emails,
                    'location': event.get('location', ''),
                    'organizer': event.get('organizer', {}),
                    'recurring_event_id': event.get('recurringEventId'),
                    'event_type': event.get('eventType', 'default'),
                    'status': event.get('status', 'confirmed')
                }
            )
            
        except Exception as e:
            print(f"Failed to convert event to issue: {e}")
            return None