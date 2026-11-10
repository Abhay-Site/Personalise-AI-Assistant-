"""
planner.py — Semantic and LLM-augmented Action Plan Generator

Transforms a user's natural language intent into a structured, executable ActionPlan.
Supports:
1. Comprehensive semantic intent detection (synonyms, appointments, agenda, inbox, etc.)
2. LLM-based structured plan decomposition using Google Gemini
3. Multi-step cross-application workflows (Calendar + Drive + Gmail)
4. Academic student workflows (Class preparation, assignment tracking)
5. Direct single-service and composite operations
"""

import re
import json
from typing import Optional
from app.schemas.chat import ActionPlanSchema, ActionStep
from app.agents.tool_registry import classify_tool
from app.utils.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────
# Semantic Intent Lexicons (Synonyms & Phrasings)
# ─────────────────────────────────────────────────────────────

CALENDAR_KEYWORDS = [
    "meeting", "schedule", "calendar", "event", "class", "appointment",
    "appointments", "agenda", "itinerary", "booking", "bookings",
    "commitment", "commitments", "availability", "free time", "slot",
    "slots", "timetable", "lecture", "seminar", "session", "interview",
    "call", "office hours", "due date", "deadline"
]

CALENDAR_PHRASES = [
    "what do i have", "what appointments", "am i free", "busy tomorrow",
    "busy today", "what's on my", "whats on my", "check my day",
    "anything planned", "what is happening", "my schedule", "free slot",
    "open slot", "when am i free", "appointments tomorrow", "appointments today"
]

DRIVE_KEYWORDS = [
    "report", "reports", "file", "files", "drive", "document", "documents",
    "doc", "docs", "notes", "pdf", "pdfs", "slides", "presentation", "deck",
    "spreadsheet", "spreadsheets", "sheet", "sheets", "excel", "syllabus",
    "paper", "manuscript", "homework", "lab manual", "folder", "personal ai assistant"
]

DRIVE_PHRASES = [
    "find the file", "look up document", "search drive", "lecture notes",
    "class slides", "reading material", "find document", "find file", "look up files"
]

EMAIL_KEYWORDS = [
    "email", "emails", "mail", "mails", "gmail", "inbox", "message",
    "messages", "thread", "threads", "draft", "drafts", "send", "dispatch",
    "forward", "reply", "notify", "ping", "write to", "participants",
    "attendees", "recipient"
]

EMAIL_PHRASES = [
    "email to", "mail to", "send to", "drop an email", "write an email",
    "check my inbox", "any unread", "messages from", "ping the",
    "notify the", "reach out to"
]


def is_email_prohibited(msg: str) -> bool:
    """Detects explicit negative constraints forbidding email actions, drafting, or modifications."""
    negative_patterns = [
        r'\b(?:do\s*not|don\'t|dont|never|no|without|stop|avoid|skip)\b.*?\b(?:email|emails|mail|draft|drafts|send|dispatch|message)\b',
        r'\b(?:do\s*not|don\'t|dont|never)\b.*?\b(?:create|write|send|dispatch|modify)\b',
        r'\bno\s+email\b',
        r'\bno\s+emails\b',
        r'\bno\s+draft\b',
        r'\bno\s+drafts\b',
        r'\bread\s+only\b',
        r'\bdo\s*not\s*modify\b',
    ]
    return any(re.search(pat, msg) for pat in negative_patterns)


def matches_calendar(msg: str) -> bool:
    """Checks if message expresses calendar, schedule, or appointment intent."""
    return any(k in msg for k in CALENDAR_KEYWORDS) or any(p in msg for p in CALENDAR_PHRASES)


def matches_drive(msg: str) -> bool:
    """Checks if message expresses Google Drive or file document intent."""
    return any(k in msg for k in DRIVE_KEYWORDS) or any(p in msg for p in DRIVE_PHRASES)


def matches_email(msg: str) -> bool:
    """Checks if message expresses email, Gmail, or messaging intent."""
    if is_email_prohibited(msg):
        return False
    has_email_addr = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg))
    return has_email_addr or any(k in msg for k in EMAIL_KEYWORDS) or any(p in msg for p in EMAIL_PHRASES)


# ─────────────────────────────────────────────────────────────
# 1. Fast Semantic Rule Planner
# ─────────────────────────────────────────────────────────────

def plan_from_semantic_rules(message: str) -> Optional[ActionPlanSchema]:
    """
    Transforms natural language requests into structured ActionPlan using rich
    semantic intent lexicons and workflow patterns.
    """
    msg = message.lower().strip()
    if not msg:
        return None

    email_prohibited = is_email_prohibited(msg)

    # 0. Direct Email Sending Workflow
    # "Send an email to user@domain.com with subject ... saying ..."
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
    is_direct_send = not email_prohibited and any(p in msg for p in ["send an email to", "email to", "send email to", "mail to", "ping ", "write to "]) and email_match

    if is_direct_send and not any(w in msg for w in ["meeting", "calendar", "tomorrow's", "schedule"]):
        recipient = email_match.group(0)
        steps = [
            ActionStep(
                order=1,
                service="gmail",
                action="create_draft",
                description=f"Create email draft to {recipient}",
                requires_approval=False,
                status="pending",
            ),
            ActionStep(
                order=2,
                service="gmail",
                action="send_email",
                description=f"Send email to {recipient}",
                requires_approval=True,
                status="pending",
            ),
        ]
        return ActionPlanSchema(
            goal=f"Compose and send email to {recipient}",
            steps=steps,
        )

    # 1. Primary Cross-App Workflow (The Master Demo)
    # "Find tomorrow's project review meeting, locate the latest Personal AI Assistant report, and prepare an email for the participants"
    has_calendar = matches_calendar(msg)
    has_drive = matches_drive(msg)
    has_email = matches_email(msg)

    if has_calendar and has_drive and has_email:
        # Cross-application chain: Calendar -> Drive -> Gmail Draft -> Gmail Send (requires approval)
        steps = [
            ActionStep(
                order=1,
                service="calendar",
                action="list_events",
                description="Find scheduled project review meeting and retrieve attendee list",
                requires_approval=False,
                status="pending",
            ),
            ActionStep(
                order=2,
                service="drive",
                action="search_files",
                description="Search Drive for the latest project report",
                requires_approval=False,
                status="pending",
            ),
            ActionStep(
                order=3,
                service="gmail",
                action="create_draft",
                description="Create email draft with report details for meeting participants",
                requires_approval=False,
                status="pending",
            ),
            ActionStep(
                order=4,
                service="gmail",
                action="send_email",
                description="Send project report email to confirmed attendees",
                requires_approval=True,
                status="pending",
            ),
        ]
        return ActionPlanSchema(
            goal="Find project meeting, locate latest report in Drive, and prepare email for participants",
            steps=steps,
        )

    # 2. Student Workflow: Prep Me for Class
    # "Prep me for AI & ML class" / "What notes do I need for class today?"
    if any(w in msg for w in ["prep me", "class prep", "prepare for class", "lecture prep", "get ready for class"]):
        steps = [
            ActionStep(
                order=1,
                service="calendar",
                action="list_events",
                description="Identify today's upcoming classes on your calendar",
                requires_approval=False,
                status="pending",
            ),
            ActionStep(
                order=2,
                service="drive",
                action="search_files",
                description="Search Google Drive for lecture notes, slides, and syllabus files",
                requires_approval=False,
                status="pending",
            ),
        ]
        return ActionPlanSchema(
            goal="Identify class schedule and retrieve preparation materials from Google Drive",
            steps=steps,
        )

    # 3. Student Workflow: Assignment Scanner
    # "Scan emails for assignments" / "Any upcoming assignment deadlines?"
    is_explicit_send = any(w in msg for w in ["send", "forward", "dispatch", "email to"])
    if not is_explicit_send and any(w in msg for w in ["assignment", "homework", "quiz", "submission deadline", "grading deadline"]):
        steps = [
            ActionStep(
                order=1,
                service="gmail",
                action="search_emails",
                description="Search Gmail for assignment notices and due dates",
                requires_approval=False,
                status="pending",
            ),
            ActionStep(
                order=2,
                service="calendar",
                action="create_event",
                description="Create calendar deadline reminders for detected assignments",
                requires_approval=False,
                status="pending",
            ),
        ]
        return ActionPlanSchema(
            goal="Scan emails for academic deadlines and prepare calendar reminders",
            steps=steps,
        )

    # 4. Standard Composite / Individual Signals
    steps: list[ActionStep] = []
    order = 1

    # Calendar signals (Supports appointments, schedule, free time, bookings, etc.)
    if has_calendar:
        is_free_time = any(w in msg for w in ["free time", "am i free", "when am i free", "availability", "open slot", "free slot", "open slots", "free slots"])
        cal_action = "find_free_time" if is_free_time else "list_events"
        cal_desc = "Find available open time slots on your calendar" if is_free_time else "Search calendar for matching events and schedule details"

        steps.append(ActionStep(
            order=order,
            service="calendar",
            action=cal_action,
            description=cal_desc,
            requires_approval=False,
            status="pending",
        ))
        order += 1

    # Drive signals (Supports files, reports, slides, notes, spreadsheets, documents, etc.)
    if has_drive:
        steps.append(ActionStep(
            order=order,
            service="drive",
            action="search_files",
            description="Locate relevant documents in Google Drive",
            requires_approval=False,
            status="pending",
        ))
        order += 1

    # Gmail signals (Supports inbox search, composing, drafts, pinging, and sending)
    if has_email:
        is_send = any(w in msg for w in ["send", "forward", "dispatch", "email to", "prepare an email", "prepare email", "draft an email", "participants", "ping"])
        if is_send:
            # First create draft (safe/write), then send (sensitive/requires approval)
            steps.append(ActionStep(
                order=order,
                service="gmail",
                action="create_draft",
                description="Compose email draft",
                requires_approval=False,
                status="pending",
            ))
            order += 1
            steps.append(ActionStep(
                order=order,
                service="gmail",
                action="send_email",
                description="Send prepared email (requires user confirmation)",
                requires_approval=True,
                status="pending",
            ))
            order += 1
        else:
            steps.append(ActionStep(
                order=order,
                service="gmail",
                action="search_emails",
                description="Search email threads and messages",
                requires_approval=False,
                status="pending",
            ))
            order += 1

    if not steps:
        return None

    goal = message[:90] + ("..." if len(message) > 90 else "")
    return ActionPlanSchema(goal=goal, steps=steps)


# ─────────────────────────────────────────────────────────────
# 2. LLM-Based Structured Plan Decomposition (Gemini)
# ─────────────────────────────────────────────────────────────

async def plan_with_gemini(message: str) -> Optional[ActionPlanSchema]:
    """
    Uses Google Gemini to decompose conversational natural language into a
    structured, multi-step ActionPlan when semantic rules do not match.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        return None

    settings = get_settings()
    if not settings.gemini_configured:
        return None

    planner_prompt = (
        "You are an AI planner for Personal AI Assistant, an agent connected to Google Calendar, Google Drive, and Gmail.\n"
        "Available actions:\n"
        "- calendar: list_events (read), find_free_time (read), create_event (write), delete_event (sensitive)\n"
        "- drive: search_files (read), get_file_metadata (read), create_file (write), delete_file (sensitive)\n"
        "- gmail: search_emails (read), get_email (read), create_draft (write), send_email (sensitive)\n\n"
        "Analyze the user's natural language request. If it requires performing tasks across calendar, drive, or gmail, "
        "output a valid JSON object with 'goal' and ordered 'steps'.\n"
        "Each step must have: 'order' (int), 'service' (str), 'action' (str), 'description' (str), 'requires_approval' (bool).\n"
        "Note: 'send_email', 'delete_event', 'delete_file' MUST have requires_approval=True.\n"
        "If the user is just saying hello or asking a general question not requiring tools, output: {}\n\n"
        f"User Request: {message}\n"
        "Output ONLY the JSON object, nothing else."
    )

    candidate_models = [settings.gemini_model, "gemini-flash-lite-latest", "gemini-3.5-flash-lite"]
    candidate_models = list(dict.fromkeys(candidate_models))

    for m_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name=m_name)
            resp = model.generate_content(
                planner_prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 400}
            )
            text = resp.text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)
            if not data or not data.get("steps"):
                return None

            steps = []
            for s in data["steps"]:
                act = s.get("action", "")
                steps.append(ActionStep(
                    order=s.get("order", len(steps) + 1),
                    service=s.get("service", "system"),
                    action=act,
                    description=s.get("description", ""),
                    requires_approval=classify_tool(act) == "sensitive" or s.get("requires_approval", False),
                    status="pending"
                ))
            return ActionPlanSchema(goal=data.get("goal", message[:80]), steps=steps)
        except Exception as err:
            logger.debug(f"Gemini planner model {m_name} error: {err}")
            continue

    return None


# ─────────────────────────────────────────────────────────────
# 3. Main Entry Points
# ─────────────────────────────────────────────────────────────

def build_plan_from_intent_sync(message: str) -> Optional[ActionPlanSchema]:
    """Synchronous plan generator using comprehensive semantic rules."""
    return plan_from_semantic_rules(message)


async def build_plan_from_intent(message: str) -> Optional[ActionPlanSchema]:
    """
    Main planner entry point:
    1. First tries instant semantic pattern analysis.
    2. If unrecognized, delegates to Gemini LLM structured planning.
    """
    plan = plan_from_semantic_rules(message)
    if plan:
        return plan

    try:
        gemini_plan = await plan_with_gemini(message)
        if gemini_plan:
            return gemini_plan
    except Exception as e:
        logger.warning(f"Gemini LLM planner fallback exception: {e}")

    return None
