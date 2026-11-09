"""
api/approvals.py — Human-in-the-Loop (HITL) approval endpoint

Enforces the core safety principle:
Sensitive operations (such as sending emails or deleting events) are never
executed autonomously. They must receive an explicit human approval.

Flow:
  User clicks Approve / Reject in the UI
      ↓
  POST /api/approvals
      ↓
  Validate ActionPlan ownership
      ↓
  Record Approval decision in database
      ↓
  If Approved:
      Execute sensitive tool with bypass_approval=True
      Update plan status to 'executed'
      Record audit log with approval_status='approved'
  If Rejected:
      Cancel execution
      Update plan status to 'rejected'
      Record audit log with approval_status='rejected'
"""

from typing import Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database import crud, models
from app.api.auth import get_mock_user
from app.schemas.approval import ApprovalRequest
from app.agents.tool_registry import execute_tool
from app.services.google_auth_service import get_user_credentials
from app.services.audit_service import log_action
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.post("")
async def handle_approval(
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """
    Process a user approval or rejection for a pending sensitive action.
    """
    # 1. Fetch target action plan
    plan = db.query(models.ActionPlan).filter(
        models.ActionPlan.id == request.action_plan_id,
        models.ActionPlan.user_id == current_user.id,
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Action plan not found")

    # Verify that the action hasn't already been executed, rejected, failed, or currently executing
    if plan.status in ("executed", "rejected", "failed", "executing"):
        raise HTTPException(
            status_code=400,
            detail=f"Action plan #{plan.id} has already been {plan.status}. Cannot execute again.",
        )

    plan_data = dict(plan.plan_json or {})
    steps = plan_data.get("steps", [])
    pending_action = plan_data.get("pending_action") or {}

    # Find the sensitive step that was awaiting approval
    sensitive_step = next((s for s in steps if s.get("requires_approval")), None)
    tool_name = (
        pending_action.get("type")
        or (sensitive_step.get("action") if sensitive_step else None)
        or "sensitive_action"
    )
    service = (
        pending_action.get("service")
        or (sensitive_step.get("service") if sensitive_step else None)
        or "system"
    )

    # 2. Record approval entity in DB
    approval_record = models.Approval(
        user_id=current_user.id,
        action_plan_id=plan.id,
        action_type=tool_name,
        approved=request.approved,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(approval_record)

    # 3. Handle Decision
    if not request.approved:
        # User REJECTED the action
        plan.status = "rejected"
        if sensitive_step:
            sensitive_step["status"] = "rejected"
        plan.plan_json = dict(plan_data)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            tool_name=tool_name,
            service=service,
            action_type="sensitive",
            status="skipped",
            conversation_id=plan.conversation_id,
            input_summary=f"User rejected execution of {tool_name}",
            result_summary="Action cancelled without execution",
            approval_required=True,
            approval_status="rejected",
        )

        # Append notification to conversation
        if plan.conversation_id:
            crud.add_message(
                db,
                conversation_id=plan.conversation_id,
                role="model",
                content=f"Action **`{tool_name}`** was **rejected** and has been cancelled. No data was modified.",
            )

        return {
            "status": "rejected",
            "action_plan_id": plan.id,
            "action_type": tool_name,
            "approved": False,
            "message": f"Action '{tool_name}' was rejected and cancelled.",
        }

    # User APPROVED the action
    # Determine the validated execution arguments:
    # 1) If user explicitly edited the action in UI modal, prioritize request.edited_action
    # 2) Otherwise use the validated arguments stored with the pending action / step
    stored_args = pending_action.get("args") or (sensitive_step.get("args") if sensitive_step else None) or {}
    exec_args = {**stored_args, **(request.edited_action or {})}

    # STRICT VALIDATION: Never substitute hardcoded or arbitrary draft IDs
    if tool_name == "send_email":
        draft_id = exec_args.get("draft_id")
        if not draft_id or not isinstance(draft_id, str) or not draft_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Cannot execute send_email: missing valid draft_id. An explicit draft must be created before sending.",
            )
        draft_id = draft_id.strip()

        # Verify draft ownership using the authenticated user identity
        from app.tools.gmail import _PENDING_DRAFTS
        if draft_id in _PENDING_DRAFTS:
            staged = _PENDING_DRAFTS[draft_id]
            if staged.get("user_id") is not None and staged.get("user_id") != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Unauthorized: draft '{draft_id}' belongs to another user.",
                )
            # Apply user edits to staged draft
            if request.edited_action:
                for k in ("to", "subject", "body", "cc"):
                    if k in request.edited_action:
                        staged[k] = request.edited_action[k]

    # Prevent concurrent execution: transition to executing state atomically
    plan.status = "executing"
    db.commit()

    exec_args_with_user = dict(exec_args)
    if tool_name in ("send_email", "create_draft"):
        exec_args_with_user["user_id"] = current_user.id

    user_creds = get_user_credentials(db, current_user)
    result = await execute_tool(
        tool_name=tool_name,
        args=exec_args_with_user,
        bypass_approval=True,
        credentials=user_creds,
    )

    # Check if tool execution failed
    is_failed = result.get("status") == "error" or (
        isinstance(result.get("data"), dict) and result["data"].get("status") == "error"
    )

    if is_failed:
        err_msg = result.get("message") or (
            result.get("data", {}).get("message") if isinstance(result.get("data"), dict) else "Execution failed"
        )
        plan.status = "failed"
        if sensitive_step:
            sensitive_step["status"] = "failed"
        plan.plan_json = dict(plan_data)
        db.commit()

        log_action(
            db=db,
            user_id=current_user.id,
            tool_name=tool_name,
            service=service,
            action_type="sensitive",
            status="failed",
            conversation_id=plan.conversation_id,
            input_summary=str(exec_args)[:200],
            result_summary=f"Execution failed: {err_msg}"[:200],
            approval_required=True,
            approval_status="approved",
        )

        if plan.conversation_id:
            crud.add_message(
                db,
                conversation_id=plan.conversation_id,
                role="model",
                content=f"❌ Action **`{tool_name}`** was approved but failed during execution: {err_msg}",
            )

        raise HTTPException(
            status_code=500,
            detail=f"Action '{tool_name}' execution failed: {err_msg}",
        )

    plan.status = "executed"
    if sensitive_step:
        sensitive_step["status"] = "done"
    plan.plan_json = dict(plan_data)
    db.commit()

    log_action(
        db=db,
        user_id=current_user.id,
        tool_name=tool_name,
        service=service,
        action_type="sensitive",
        status="success",
        conversation_id=plan.conversation_id,
        input_summary=str(exec_args)[:200],
        result_summary=f"Action '{tool_name}' executed after human approval",
        approval_required=True,
        approval_status="approved",
    )

    # Append notification to conversation
    if plan.conversation_id:
        crud.add_message(
            db,
            conversation_id=plan.conversation_id,
            role="model",
            content=f"✓ Action **`{tool_name}`** was **approved** and executed successfully.",
        )

    return {
        "status": "executed",
        "action_plan_id": plan.id,
        "action_type": tool_name,
        "approved": True,
        "execution_result": result,
        "message": f"Action '{tool_name}' approved and executed successfully.",
    }
