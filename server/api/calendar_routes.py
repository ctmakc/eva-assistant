"""Calendar API routes for EVA."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


@router.get("/auth")
async def calendar_auth():
    """Start Google Calendar OAuth flow."""
    from integrations.calendar import get_calendar_integration

    calendar = get_calendar_integration()
    try:
        auth_url = calendar.get_auth_url()
        return RedirectResponse(url=auth_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback")
async def calendar_callback(code: str = Query(...)):
    """Handle OAuth callback from Google."""
    from integrations.calendar import get_calendar_integration

    calendar = get_calendar_integration()
    success = calendar.handle_callback(code)

    if success:
        return RedirectResponse(url="/dashboard?calendar_connected=1")
    else:
        raise HTTPException(status_code=400, detail="OAuth failed")


@router.get("/status")
async def calendar_status():
    """Check calendar connection status."""
    from integrations.calendar import get_calendar_integration

    calendar = get_calendar_integration()
    return {
        "authenticated": calendar.is_authenticated
    }


@router.get("/today")
async def get_today():
    """Get today's calendar events."""
    from integrations.calendar import get_calendar_integration

    calendar = get_calendar_integration()
    if not calendar.is_authenticated:
        raise HTTPException(status_code=401, detail="Calendar not connected")

    result = await calendar.get_today_events()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.get("/upcoming")
async def get_upcoming(days: int = 7, limit: int = 10):
    """Get upcoming calendar events."""
    from integrations.calendar import get_calendar_integration

    calendar = get_calendar_integration()
    if not calendar.is_authenticated:
        raise HTTPException(status_code=401, detail="Calendar not connected")

    result = await calendar.get_upcoming_events(days=days, max_results=limit)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.post("/event")
async def create_event(
    summary: str,
    start_time: str,
    duration_minutes: int = 60,
    description: str = "",
    location: str = ""
):
    """Create a new calendar event."""
    from integrations.calendar import get_calendar_integration

    calendar = get_calendar_integration()
    if not calendar.is_authenticated:
        raise HTTPException(status_code=401, detail="Calendar not connected")

    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_time format")

    result = await calendar.create_event(
        summary=summary,
        start_time=start_dt,
        end_time=end_dt,
        description=description,
        location=location
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result
