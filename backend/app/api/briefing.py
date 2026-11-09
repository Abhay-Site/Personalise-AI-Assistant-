"""
api/briefing.py — Proactive Morning Briefing and Conflict Detection endpoints

Endpoints:
- GET /api/briefing — Returns unified daily briefing (calendar, mail, drive, conflicts)
- GET /api/briefing/conflicts — Returns detected schedule conflicts
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database import models
from app.api.auth import get_mock_user
from app.services.google_auth_service import get_user_credentials
from app.services.briefing_service import generate_morning_briefing
from app.services.conflict_service import detect_schedule_conflicts
from datetime import datetime, timezone, timedelta
from app.tools import calendar

router = APIRouter(prefix="/api/briefing", tags=["briefing"])


@router.get("")
async def get_briefing(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """
    Returns the user's daily morning briefing synthesizing Calendar, Gmail, and Drive.
    """
    creds = get_user_credentials(db, current_user)
    return await generate_morning_briefing(credentials=creds, user_name=current_user.name)


@router.get("/conflicts")
async def get_conflicts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """
    Scans the user's calendar and reports any schedule collisions or overlapping meetings.
    """
    creds = get_user_credentials(db, current_user)
    now = datetime.now(timezone.utc)
    month_start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    month_end = (now + timedelta(days=30)).replace(hour=23, minute=59, second=59, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    cal_data = await calendar.list_events(
        time_min=month_start,
        time_max=month_end,
        credentials=creds,
    )
    events = cal_data.get("events", [])
    conflicts = detect_schedule_conflicts(events)
    return {
        "count": len(conflicts),
        "conflicts": conflicts,
    }
