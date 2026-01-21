"""Gmail integration with OAuth2 for EVA assistant."""

import os
import json
import base64
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import get_settings
from integrations.vault import get_vault

logger = logging.getLogger("eva.gmail")

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.labels'
]


class GmailIntegration:
    """Handles Gmail OAuth and email operations."""

    def __init__(self):
        self.settings = get_settings()
        self.vault = get_vault()
        self._service = None
        self._credentials: Optional[Credentials] = None

    @property
    def is_configured(self) -> bool:
        """Check if Gmail OAuth is configured."""
        creds = self.vault.get("gmail_oauth")
        return creds is not None and "client_id" in creds

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid auth tokens."""
        tokens = self.vault.get("gmail_tokens")
        return tokens is not None and "access_token" in tokens

    def configure_oauth(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Configure OAuth credentials.
        These come from Google Cloud Console.
        """
        self.vault.store("gmail_oauth", {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri
        })
        logger.info("Gmail OAuth configured")

    def get_auth_url(self) -> Optional[str]:
        """
        Get OAuth authorization URL.
        User needs to visit this URL to grant access.
        """
        oauth_creds = self.vault.get("gmail_oauth")
        if not oauth_creds:
            return None

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": oauth_creds["client_id"],
                    "client_secret": oauth_creds["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [oauth_creds["redirect_uri"]]
                }
            },
            scopes=SCOPES,
            redirect_uri=oauth_creds["redirect_uri"]
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        return auth_url

    def handle_callback(self, code: str) -> bool:
        """
        Handle OAuth callback with authorization code.
        Exchange code for tokens.
        """
        oauth_creds = self.vault.get("gmail_oauth")
        if not oauth_creds:
            return False

        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": oauth_creds["client_id"],
                        "client_secret": oauth_creds["client_secret"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [oauth_creds["redirect_uri"]]
                    }
                },
                scopes=SCOPES,
                redirect_uri=oauth_creds["redirect_uri"]
            )

            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Store tokens in vault
            self.vault.store("gmail_tokens", {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": list(credentials.scopes) if credentials.scopes else SCOPES
            })

            self._credentials = credentials
            logger.info("Gmail OAuth tokens stored successfully")
            return True

        except Exception as e:
            logger.error(f"Gmail OAuth callback failed: {e}")
            return False

    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh credentials."""
        if self._credentials and self._credentials.valid:
            return self._credentials

        tokens = self.vault.get("gmail_tokens")
        if not tokens:
            return None

        self._credentials = Credentials(
            token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            token_uri=tokens.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=tokens.get("client_id"),
            client_secret=tokens.get("client_secret"),
            scopes=tokens.get("scopes", SCOPES)
        )

        # Refresh if expired
        if self._credentials.expired and self._credentials.refresh_token:
            try:
                from google.auth.transport.requests import Request
                self._credentials.refresh(Request())

                # Update stored tokens
                self.vault.store("gmail_tokens", {
                    "access_token": self._credentials.token,
                    "refresh_token": self._credentials.refresh_token,
                    "token_uri": self._credentials.token_uri,
                    "client_id": self._credentials.client_id,
                    "client_secret": self._credentials.client_secret,
                    "scopes": list(self._credentials.scopes) if self._credentials.scopes else SCOPES
                })
            except Exception as e:
                logger.error(f"Failed to refresh Gmail token: {e}")
                return None

        return self._credentials

    def _get_service(self):
        """Get Gmail API service."""
        if self._service:
            return self._service

        credentials = self._get_credentials()
        if not credentials:
            return None

        self._service = build('gmail', 'v1', credentials=credentials)
        return self._service

    async def get_unread_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get unread emails from inbox."""
        service = self._get_service()
        if not service:
            return []

        try:
            results = service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                email_data = await self._get_email_details(msg['id'])
                if email_data:
                    emails.append(email_data)

            return emails

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []

    async def _get_email_details(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific email."""
        service = self._get_service()
        if not service:
            return None

        try:
            message = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}

            return {
                'id': msg_id,
                'from': headers.get('From', 'Unknown'),
                'subject': headers.get('Subject', 'No subject'),
                'date': headers.get('Date', ''),
                'snippet': message.get('snippet', ''),
                'labels': message.get('labelIds', [])
            }

        except HttpError as e:
            logger.error(f"Failed to get email {msg_id}: {e}")
            return None

    async def get_email_body(self, msg_id: str) -> str:
        """Get full email body."""
        service = self._get_service()
        if not service:
            return ""

        try:
            message = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            payload = message.get('payload', {})
            body = ""

            if 'body' in payload and payload['body'].get('data'):
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            elif 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break

            return body

        except Exception as e:
            logger.error(f"Failed to get email body: {e}")
            return ""

    async def send_email(self, to: str, subject: str, body: str, html: bool = False) -> bool:
        """Send an email."""
        service = self._get_service()
        if not service:
            return False

        try:
            message = MIMEMultipart('alternative')
            message['To'] = to
            message['Subject'] = subject

            if html:
                message.attach(MIMEText(body, 'html'))
            else:
                message.attach(MIMEText(body, 'plain'))

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            logger.info(f"Email sent to {to}")
            return True

        except HttpError as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def mark_as_read(self, msg_id: str) -> bool:
        """Mark email as read."""
        service = self._get_service()
        if not service:
            return False

        try:
            service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except HttpError as e:
            logger.error(f"Failed to mark email as read: {e}")
            return False

    async def get_important_emails(self, max_results: int = 5) -> List[Dict[str, Any]]:
        """Get important/priority emails."""
        service = self._get_service()
        if not service:
            return []

        try:
            # Search for important or starred emails
            results = service.users().messages().list(
                userId='me',
                q='is:important OR is:starred is:unread',
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                email_data = await self._get_email_details(msg['id'])
                if email_data:
                    emails.append(email_data)

            return emails

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []

    def disconnect(self):
        """Remove Gmail integration."""
        self.vault.delete("gmail_oauth")
        self.vault.delete("gmail_tokens")
        self._service = None
        self._credentials = None
        logger.info("Gmail disconnected")


# Singleton
_gmail: Optional[GmailIntegration] = None


def get_gmail_integration() -> GmailIntegration:
    global _gmail
    if _gmail is None:
        _gmail = GmailIntegration()
    return _gmail
