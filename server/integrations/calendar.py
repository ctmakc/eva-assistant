"""Google Calendar integration for EVA."""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("eva.calendar")

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
          'https://www.googleapis.com/auth/calendar.events']


class GoogleCalendarIntegration:
    """Google Calendar integration."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.credentials_file = os.path.join(data_dir, "calendar_credentials.json")
        self.token_file = os.path.join(data_dir, "calendar_token.json")
        self.credentials: Optional[Credentials] = None
        self.service = None
        self.oauth_config: Dict[str, str] = {}
        self._load_token()

    def _load_token(self):
        """Load saved token if exists."""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    self.credentials = Credentials.from_authorized_user_info(token_data, SCOPES)
                    if self.credentials and self.credentials.valid:
                        self.service = build('calendar', 'v3', credentials=self.credentials)
                        logger.info("Calendar credentials loaded")
            except Exception as e:
                logger.error(f"Failed to load calendar token: {e}")

    def _save_token(self):
        """Save token for future use."""
        if self.credentials:
            with open(self.token_file, 'w') as f:
                f.write(self.credentials.to_json())

    @property
    def is_authenticated(self) -> bool:
        return self.credentials is not None and self.credentials.valid

    def configure_oauth(self, client_id: str, client_secret: str, redirect_uri: str):
        """Configure OAuth settings."""
        self.oauth_config = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri
        }

        # Save OAuth config
        from integrations.vault import get_vault
        vault = get_vault()
        vault.store("calendar_oauth", self.oauth_config)

    def get_auth_url(self) -> str:
        """Get OAuth authorization URL."""
        if not self.oauth_config:
            # Try to load from vault
            from integrations.vault import get_vault
            vault = get_vault()
            self.oauth_config = vault.get("calendar_oauth") or {}

        if not self.oauth_config.get("client_id"):
            raise ValueError("OAuth not configured")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.oauth_config["client_id"],
                    "client_secret": self.oauth_config["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.oauth_config["redirect_uri"]]
                }
            },
            scopes=SCOPES,
            redirect_uri=self.oauth_config["redirect_uri"]
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url

    def handle_callback(self, code: str) -> bool:
        """Handle OAuth callback."""
        try:
            if not self.oauth_config:
                from integrations.vault import get_vault
                vault = get_vault()
                self.oauth_config = vault.get("calendar_oauth") or {}

            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.oauth_config["client_id"],
                        "client_secret": self.oauth_config["client_secret"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.oauth_config["redirect_uri"]]
                    }
                },
                scopes=SCOPES,
                redirect_uri=self.oauth_config["redirect_uri"]
            )

            flow.fetch_token(code=code)
            self.credentials = flow.credentials
            self._save_token()

            self.service = build('calendar', 'v3', credentials=self.credentials)
            logger.info("Calendar authenticated successfully")
            return True

        except Exception as e:
            logger.error(f"Calendar OAuth failed: {e}")
            return False

    async def get_upcoming_events(self, days: int = 7, max_results: int = 10) -> Dict[str, Any]:
        """Get upcoming calendar events."""
        if not self.is_authenticated:
            return {"success": False, "error": "Not authenticated"}

        try:
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days)).isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            parsed_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                # Parse datetime
                if 'T' in start:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    is_all_day = False
                else:
                    start_dt = datetime.strptime(start, '%Y-%m-%d')
                    is_all_day = True

                parsed_events.append({
                    "id": event['id'],
                    "summary": event.get('summary', 'No title'),
                    "description": event.get('description', ''),
                    "start": start,
                    "end": end,
                    "start_datetime": start_dt.isoformat(),
                    "is_all_day": is_all_day,
                    "location": event.get('location', ''),
                    "link": event.get('htmlLink', '')
                })

            return {
                "success": True,
                "events": parsed_events,
                "count": len(parsed_events)
            }

        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            return {"success": False, "error": str(e)}

    async def get_today_events(self) -> Dict[str, Any]:
        """Get today's events."""
        if not self.is_authenticated:
            return {"success": False, "error": "Not authenticated"}

        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=today_start.isoformat() + 'Z',
                timeMax=today_end.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            parsed = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                if 'T' in start:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    time_str = start_dt.strftime('%H:%M')
                else:
                    time_str = "весь день"

                parsed.append({
                    "summary": event.get('summary', 'Без названия'),
                    "time": time_str,
                    "location": event.get('location', '')
                })

            return {
                "success": True,
                "events": parsed,
                "count": len(parsed)
            }

        except HttpError as e:
            return {"success": False, "error": str(e)}

    async def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime = None,
        description: str = "",
        location: str = ""
    ) -> Dict[str, Any]:
        """Create a calendar event."""
        if not self.is_authenticated:
            return {"success": False, "error": "Not authenticated"}

        try:
            if end_time is None:
                end_time = start_time + timedelta(hours=1)

            event = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Europe/Kiev',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Europe/Kiev',
                },
            }

            created = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            return {
                "success": True,
                "event_id": created['id'],
                "link": created.get('htmlLink', '')
            }

        except HttpError as e:
            logger.error(f"Failed to create event: {e}")
            return {"success": False, "error": str(e)}

    def format_events(self, events_data: Dict[str, Any]) -> str:
        """Format events for voice output."""
        if not events_data.get("success"):
            return f"Не удалось получить события: {events_data.get('error', 'unknown')}"

        events = events_data.get("events", [])
        if not events:
            return "У тебя нет запланированных событий."

        lines = [f"У тебя {len(events)} событий:"]

        # Group by day
        current_day = None
        for event in events:
            start = event.get("start_datetime") or event.get("start")
            if 'T' in str(start):
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                day = dt.strftime('%Y-%m-%d')
                time = dt.strftime('%H:%M')
            else:
                day = start
                time = "весь день"

            if day != current_day:
                current_day = day
                day_dt = datetime.strptime(day[:10], '%Y-%m-%d')
                if day_dt.date() == datetime.now().date():
                    day_name = "Сегодня"
                elif day_dt.date() == (datetime.now() + timedelta(days=1)).date():
                    day_name = "Завтра"
                else:
                    day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
                    day_name = f"{day_names[day_dt.weekday()]}, {day_dt.strftime('%d.%m')}"
                lines.append(f"\n📅 {day_name}:")

            summary = event.get("summary", "Без названия")
            lines.append(f"  • {time} - {summary}")

        return "\n".join(lines)

    def format_today(self, events_data: Dict[str, Any]) -> str:
        """Format today's events."""
        if not events_data.get("success"):
            return f"Не удалось получить расписание: {events_data.get('error', 'unknown')}"

        events = events_data.get("events", [])
        if not events:
            return "На сегодня ничего не запланировано. Свободный день!"

        lines = ["📅 Сегодня у тебя:"]
        for event in events:
            time = event.get("time", "")
            summary = event.get("summary", "")
            lines.append(f"  • {time} - {summary}")

        return "\n".join(lines)


# Singleton
_calendar: Optional[GoogleCalendarIntegration] = None


def get_calendar_integration() -> GoogleCalendarIntegration:
    global _calendar
    if _calendar is None:
        from config import get_settings
        settings = get_settings()
        _calendar = GoogleCalendarIntegration(settings.data_dir)
    return _calendar
