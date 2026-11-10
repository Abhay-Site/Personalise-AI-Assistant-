"""
api/workflows.py — Pre-configured & saved workflows catalog

Provides:
- Templates for student and cross-application workflows
- Direct workflow execution endpoint
- History of executed action plans
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database import crud, models
from app.api.auth import get_mock_user
from app.api.chat import chat
from app.schemas.chat import ChatRequest, ChatResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

WORKFLOW_TEMPLATES = [
    {
        "id": "master-demo",
        "title": "Master Cross-App Coordination",
        "category": "cross-app",
        "icon": "🚀",
        "description": "Finds tomorrow's project review meeting, locates the latest report in Drive, and drafts an email with attendees.",
        "prompt": "Find tomorrow's project review meeting, locate the latest Personal AI Assistant report, and prepare an email for the participants",
        "services": ["calendar", "drive", "gmail"],
    },
    {
        "id": "prep-for-class",
        "title": "Prep Me for Class",
        "category": "academic",
        "icon": "🎓",
        "description": "Inspects today's schedule for upcoming lectures and retrieves matching lecture notes/slides from Drive.",
        "prompt": "Prep me for today's AI & ML class by finding relevant notes in Drive",
        "services": ["calendar", "drive"],
    },
    {
        "id": "assignment-scanner",
        "title": "Assignment Scanner",
        "category": "academic",
        "icon": "📝",
        "description": "Scans inbox for course assignment announcements and prepares calendar deadline reminders.",
        "prompt": "Scan my emails for assignment deadlines and add reminders to my calendar",
        "services": ["gmail", "calendar"],
    },
]


@router.get("")
def list_workflow_templates():
    """Returns available pre-configured workflow templates."""
    return WORKFLOW_TEMPLATES


@router.get("/history")
def get_workflow_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """Returns the history of generated action plans and their execution statuses."""
    plans = (
        db.query(models.ActionPlan)
        .filter(models.ActionPlan.user_id == current_user.id)
        .order_by(models.ActionPlan.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": p.id,
            "conversation_id": p.conversation_id,
            "goal": p.plan_json.get("goal") if p.plan_json else "Workflow Plan",
            "steps_count": len(p.plan_json.get("steps", [])) if p.plan_json else 0,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in plans
    ]


@router.post("/run", response_model=ChatResponse)
async def run_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """Directly triggers a workflow template by ID."""
    template = next((t for t in WORKFLOW_TEMPLATES if t["id"] == workflow_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    request = ChatRequest(message=template["prompt"])
    return await chat(request=request, db=db, current_user=current_user)
