"""
api/audit.py — Audit log querying and filtering endpoints

GET /api/audit:
  Filters:
    - service: gmail | calendar | drive | system
    - status: success | failed | skipped
    - approval_status: approved | rejected
    - q: keyword search in tool name, input or result summary
    - limit: max records
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database import crud
from app.api.auth import get_mock_user
from app.database.models import User
from app.schemas.approval import AuditLogSchema

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogSchema])
def list_audit_logs(
    service: str | None = Query(None, description="Filter by service: gmail | calendar | drive | system"),
    status: str | None = Query(None, description="Filter by status: success | failed | skipped"),
    approval_status: str | None = Query(None, description="Filter by approval status: approved | rejected"),
    q: str | None = Query(None, description="Search keyword across tool name and summary"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_mock_user),
):
    """
    Returns the sanitized audit trail for the active user with optional filtering.
    """
    return crud.get_audit_logs(
        db,
        user_id=current_user.id,
        service=service,
        status=status,
        approval_status=approval_status,
        search=q,
        limit=limit,
    )
