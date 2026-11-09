"""
services/briefing_service.py — Proactive Morning Briefing Synthesis

Aggregates across:
1. Google Calendar (today's meetings & classes)
2. Gmail (urgent messages & deadline announcements)
3. Google Drive (relevant notes, documents, and slides)
4. Conflict Auditor (schedule clashes)
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from app.tools import calendar, gmail, drive
from app.services.conflict_service import detect_schedule_conflicts
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def generate_morning_briefing(credentials=None, user_name: str = "Student") -> Dict[str, Any]:
    """
    Synthesizes a proactive morning briefing summarizing calendar, email, and files.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0).isoformat()
    today_end = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()

    # 1. Fetch Calendar events
    cal_data = await calendar.list_events(time_min=today_start, time_max=today_end, credentials=credentials)
    events = cal_data.get("events", [])

    # 2. Fetch Urgent Emails
    mail_data = await gmail.search_emails(query="deadline OR meeting OR urgent OR assignment", credentials=credentials)
    messages = mail_data.get("messages", [])

    # 3. Fetch Relevant Drive Files
    drive_data = await drive.search_files(query="report OR notes OR syllabus", credentials=credentials)
    files = drive_data.get("files", [])

    # 4. Check for Schedule Conflicts
    conflicts = detect_schedule_conflicts(events)

    # 5. Format AI Summary
    summary_lines = [
        f"☀️ Good morning, {user_name}!",
        f"You have {len(events)} event(s) scheduled on your calendar today.",
    ]
    if conflicts:
        summary_lines.append(f"⚠️ Note: {len(conflicts)} schedule conflict detected that requires your attention.")
    if messages:
        summary_lines.append(f"📬 You have {len(messages)} important academic/project email(s) to review.")
    if files:
        summary_lines.append(f"📁 {len(files)} relevant documents found in Google Drive ready for your tasks.")

    return {
        "date": now.strftime("%A, %B %d, %Y"),
        "greeting": f"Good morning, {user_name}!",
        "ai_summary": "\n".join(summary_lines),
        "events": events,
        "important_emails": messages,
        "recommended_files": files,
        "conflicts": conflicts,
        "stats": {
            "events_count": len(events),
            "emails_count": len(messages),
            "files_count": len(files),
            "conflicts_count": len(conflicts),
        },
    }
