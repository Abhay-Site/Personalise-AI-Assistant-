"""schemas/approval.py — Pydantic models for the human-in-the-loop approval system"""

from datetime import datetime
from pydantic import BaseModel


class ApprovalRequest(BaseModel):
    action_plan_id: int
    approved: bool
    edited_action: dict | None = None  # Optional: user-edited version of the action


class ApprovalResponse(BaseModel):
    id: int
    action_plan_id: int
    action_type: str
    approved: bool
    approved_at: datetime

    model_config = {"from_attributes": True}


class AuditLogSchema(BaseModel):
    id: int
    action_type: str
    service: str
    tool_name: str
    input_summary: str | None
    result_summary: str | None
    status: str
    approval_required: bool
    approval_status: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
