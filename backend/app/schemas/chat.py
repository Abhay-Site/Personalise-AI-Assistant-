"""
schemas/chat.py — Pydantic models for the /api/chat endpoint

These define the shape of data going IN and OUT of the chat API.
Pydantic validates all fields automatically, so bad requests are rejected early.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


# ── Incoming ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000, description="The user's natural-language message")
    conversation_id: int | None = Field(None, description="Existing conversation to continue, or None to start new")


# ── Execution Trace ───────────────────────────────────────────

class TraceStep(BaseModel):
    """A single visible step in the agent's execution trace."""
    status: str  # "ok" | "warning" | "error" | "pending"
    message: str  # Human-readable description (e.g. "Calendar searched")
    detail: str | None = None


# ── Action Plan ───────────────────────────────────────────────

class ActionStep(BaseModel):
    order: int
    service: str   # gmail | calendar | drive | system
    action: str
    description: str | None = None
    requires_approval: bool = False
    status: str = "pending"  # pending | running | done | failed | awaiting_approval
    args: dict[str, Any] | None = None


class ActionPlanSchema(BaseModel):
    goal: str
    steps: list[ActionStep]


# ── Outgoing ──────────────────────────────────────────────────

class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    reply: str = Field(..., description="The assistant's text reply")
    action_plan_id: int | None = None
    action_plan: ActionPlanSchema | None = None
    trace: list[TraceStep] = Field(default_factory=list)
    requires_approval: bool = False
    approval_action: dict[str, Any] | None = None  # Details of what needs approval
    integration_status: str = "connected"  # "connected" | "fallback" | "demo"
    model_name: str | None = None
    is_fallback: bool = False
    error_detail: str | None = None


# ── Message history ───────────────────────────────────────────

class MessageSchema(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
