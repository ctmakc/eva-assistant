"""Gmail API routes for EVA assistant."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Form, Query
from fastapi.responses import RedirectResponse
from typing import Optional

from auth import require_auth
from integrations.gmail import get_gmail_integration

logger = logging.getLogger("eva.api.gmail")

router = APIRouter(prefix="/api/v1/gmail", tags=["gmail"])


# ============== Configuration ==============

@router.get("/status")
async def gmail_status():
    """Get Gmail integration status."""
    gmail = get_gmail_integration()

    return {
        "configured": gmail.is_configured,
        "authenticated": gmail.is_authenticated,
        "message": _get_status_message(gmail)
    }


def _get_status_message(gmail) -> str:
    if not gmail.is_configured:
        return "Gmail OAuth not configured. Use POST /api/v1/gmail/configure"
    if not gmail.is_authenticated:
        return "Gmail not authenticated. Visit /api/v1/gmail/auth to authorize"
    return "Gmail connected and ready"


@router.post("/configure")
async def configure_gmail(
    client_id: str = Form(...),
    client_secret: str = Form(...),
    redirect_uri: str = Form(...),
    _: bool = Depends(require_auth)
):
    """
    Configure Gmail OAuth credentials.

    Get these from Google Cloud Console:
    1. Create a project at console.cloud.google.com
    2. Enable Gmail API
    3. Create OAuth 2.0 credentials (Web application)
    4. Add redirect URI: http://YOUR_SERVER:8080/api/v1/gmail/callback
    """
    gmail = get_gmail_integration()
    gmail.configure_oauth(client_id, client_secret, redirect_uri)

    return {
        "success": True,
        "message": "Gmail OAuth configured. Now visit /api/v1/gmail/auth to authorize",
        "next_step": "/api/v1/gmail/auth"
    }


@router.get("/auth")
async def gmail_auth():
    """
    Start Gmail OAuth flow.
    Redirects to Google for authorization.
    """
    gmail = get_gmail_integration()

    if not gmail.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Gmail OAuth not configured. Use POST /configure first"
        )

    auth_url = gmail.get_auth_url()
    if not auth_url:
        raise HTTPException(status_code=500, detail="Failed to generate auth URL")

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def gmail_callback(code: str = Query(...), error: str = Query(default=None)):
    """
    OAuth callback from Google.
    Exchanges authorization code for tokens.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    gmail = get_gmail_integration()

    if gmail.handle_callback(code):
        return {
            "success": True,
            "message": "Gmail connected successfully! EVA can now read and send emails."
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to complete OAuth flow")


@router.delete("/disconnect")
async def disconnect_gmail(_: bool = Depends(require_auth)):
    """Disconnect Gmail integration."""
    gmail = get_gmail_integration()
    gmail.disconnect()

    return {"success": True, "message": "Gmail disconnected"}


# ============== Email Operations ==============

@router.get("/unread")
async def get_unread_emails(
    max_results: int = Query(default=10, le=50),
    _: bool = Depends(require_auth)
):
    """Get unread emails."""
    gmail = get_gmail_integration()

    if not gmail.is_authenticated:
        raise HTTPException(status_code=401, detail="Gmail not authenticated")

    emails = await gmail.get_unread_emails(max_results)

    return {
        "count": len(emails),
        "emails": emails
    }


@router.get("/important")
async def get_important_emails(
    max_results: int = Query(default=5, le=20),
    _: bool = Depends(require_auth)
):
    """Get important/priority emails."""
    gmail = get_gmail_integration()

    if not gmail.is_authenticated:
        raise HTTPException(status_code=401, detail="Gmail not authenticated")

    emails = await gmail.get_important_emails(max_results)

    return {
        "count": len(emails),
        "emails": emails
    }


@router.get("/email/{msg_id}")
async def get_email_body(msg_id: str, _: bool = Depends(require_auth)):
    """Get full email body."""
    gmail = get_gmail_integration()

    if not gmail.is_authenticated:
        raise HTTPException(status_code=401, detail="Gmail not authenticated")

    body = await gmail.get_email_body(msg_id)

    return {
        "id": msg_id,
        "body": body
    }


@router.post("/send")
async def send_email(
    to: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    html: bool = Form(default=False),
    _: bool = Depends(require_auth)
):
    """Send an email."""
    gmail = get_gmail_integration()

    if not gmail.is_authenticated:
        raise HTTPException(status_code=401, detail="Gmail not authenticated")

    success = await gmail.send_email(to, subject, body, html)

    if success:
        return {"success": True, "message": f"Email sent to {to}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")


@router.post("/mark-read/{msg_id}")
async def mark_as_read(msg_id: str, _: bool = Depends(require_auth)):
    """Mark email as read."""
    gmail = get_gmail_integration()

    if not gmail.is_authenticated:
        raise HTTPException(status_code=401, detail="Gmail not authenticated")

    success = await gmail.mark_as_read(msg_id)

    if success:
        return {"success": True, "message": "Email marked as read"}
    else:
        raise HTTPException(status_code=500, detail="Failed to mark email as read")


# ============== EVA-friendly endpoints ==============

@router.get("/summary")
async def email_summary(_: bool = Depends(require_auth)):
    """
    Get email summary for EVA to report.
    Returns counts and highlights.
    """
    gmail = get_gmail_integration()

    if not gmail.is_authenticated:
        return {
            "connected": False,
            "message": "Gmail не подключен"
        }

    unread = await gmail.get_unread_emails(20)
    important = await gmail.get_important_emails(5)

    # Extract unique senders
    senders = list(set(e['from'].split('<')[0].strip() for e in unread[:5]))

    return {
        "connected": True,
        "unread_count": len(unread),
        "important_count": len(important),
        "recent_senders": senders,
        "important_subjects": [e['subject'] for e in important[:3]],
        "summary": _generate_summary(unread, important)
    }


def _generate_summary(unread: list, important: list) -> str:
    """Generate human-readable summary for EVA."""
    if not unread and not important:
        return "Нет новых писем"

    parts = []

    if important:
        parts.append(f"{len(important)} важных")

    if unread:
        parts.append(f"{len(unread)} непрочитанных")

    summary = f"У тебя {' и '.join(parts)} писем"

    if important:
        subject = important[0]['subject'][:50]
        sender = important[0]['from'].split('<')[0].strip()
        summary += f". Важное от {sender}: \"{subject}\""

    return summary
