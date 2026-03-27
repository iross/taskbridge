"""Google Calendar integration for TaskBridge.

Fetches events for a given day using the Google Calendar API with OAuth2.
Credentials are stored in ~/.taskbridge/gcal_token.json after first-time auth.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


@dataclass
class CalendarEvent:
    """A single calendar event."""

    title: str
    start: datetime
    end: datetime


class GoogleCalendarClient:
    """Google Calendar API client with OAuth2 authentication."""

    def __init__(self, credentials_path: str, token_path: str):
        """
        Args:
            credentials_path: Path to OAuth2 client credentials JSON (downloaded from Google Cloud).
            token_path: Path where the access token is cached after first auth.
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)

    def authenticate(self):
        """Authenticate and return credentials, refreshing or running OAuth flow as needed."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as e:
            raise RuntimeError(
                "Google API libraries not installed. "
                "Run: uv add google-auth-oauthlib google-api-python-client"
            ) from e

        creds = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise RuntimeError(
                        f"Google Calendar credentials not found at {self.credentials_path}.\n"
                        "Run 'taskbridge config gcal' to configure."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_path, "w") as f:
                f.write(creds.to_json())

        return creds

    def get_events(self, date: datetime, calendar_id: str = "primary") -> list[CalendarEvent]:
        """Fetch all events for the given date from Google Calendar.

        Args:
            date: The day to fetch events for (time components are ignored).
            calendar_id: Google Calendar ID (default: "primary").

        Returns:
            List of CalendarEvent sorted by start time.
        """
        try:
            from googleapiclient.discovery import build
        except ImportError as e:
            raise RuntimeError(
                "Google API libraries not installed. "
                "Run: uv add google-auth-oauthlib google-api-python-client"
            ) from e

        import dateutil.parser

        creds = self.authenticate()
        service = build("calendar", "v3", credentials=creds)

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=start_of_day.isoformat() + "Z",
                timeMax=end_of_day.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = []
        for item in result.get("items", []):
            start_raw = item["start"].get("dateTime") or item["start"].get("date")
            end_raw = item["end"].get("dateTime") or item["end"].get("date")
            if not start_raw or not end_raw:
                continue

            try:
                start_dt = dateutil.parser.parse(start_raw)
                end_dt = dateutil.parser.parse(end_raw)
                # Convert tz-aware datetimes to naive local time
                if start_dt.tzinfo is not None:
                    start_dt = start_dt.astimezone().replace(tzinfo=None)
                if end_dt.tzinfo is not None:
                    end_dt = end_dt.astimezone().replace(tzinfo=None)
            except (ValueError, OverflowError):
                continue

            events.append(
                CalendarEvent(
                    title=item.get("summary", "(no title)"),
                    start=start_dt,
                    end=end_dt,
                )
            )

        return events
