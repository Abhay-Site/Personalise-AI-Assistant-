"""schemas/workflow.py — Pydantic models for workflows and action plans"""

from datetime import datetime
from pydantic import BaseModel


class ActionStepSchema(BaseModel):
    order: int
    service: str
    action: str
    description: str | None = None
    requires_approval: bool = False
    status: str = "pending"


class WorkflowSchema(BaseModel):
    id: int
    goal: str
    steps: list[ActionStepSchema]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
