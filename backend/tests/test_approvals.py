"""
tests/test_approvals.py — Tests for Human-in-the-Loop approvals and tool execution
"""

import pytest

def test_sensitive_action_plan_stores_and_requires_approval(client):
    """
    Triggering a workflow with a sensitive action (send_email) must:
    1. Mark requires_approval = True
    2. Save an action plan in the database with pending status
    """
    response = client.post("/api/chat", json={
        "message": "Find tomorrow's project review meeting, locate the latest Personal AI Assistant report, and prepare an email for the participants"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["requires_approval"] is True
    assert data["approval_action"] is not None
    assert data["approval_action"]["type"] == "send_email"
    assert data["action_plan"] is not None
    assert data["action_plan_id"] is not None


def test_approval_endpoint_approve(client):
    """
    Approving a pending action plan should:
    1. Update status to 'executed'
    2. Record an approval entry in DB
    3. Return execution success
    """
    # 1. Trigger sensitive action to create plan
    chat_resp = client.post("/api/chat", json={
        "message": "Send an email to my professor about the project deadline"
    })
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["requires_approval"] is True
    plan_id = data["action_plan_id"]
    assert plan_id is not None

    # 2. Call approval endpoint with approved=True
    approval_resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": True
    })
    assert approval_resp.status_code == 200
    res_data = approval_resp.json()
    assert res_data["status"] == "executed"
    assert res_data["approved"] is True
    assert "successfully" in res_data["message"]


def test_approval_endpoint_reject(client):
    """
    Rejecting a pending action plan should:
    1. Update status to 'rejected'
    2. Record rejection in DB
    3. Cancel execution without modifying data
    """
    chat_resp = client.post("/api/chat", json={
        "message": "Send an email to the team regarding tomorrow's meeting"
    })
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["requires_approval"] is True
    plan_id = data["action_plan_id"]
    assert plan_id is not None

    # Reject the action
    approval_resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": False
    })
    assert approval_resp.status_code == 200
    res_data = approval_resp.json()
    assert res_data["status"] == "rejected"
    assert res_data["approved"] is False
    assert "cancelled" in res_data["message"]


def test_approval_cannot_execute_twice(client):
    """Verifies that an action plan cannot be executed multiple times."""
    chat_resp = client.post("/api/chat", json={
        "message": "Send an email to supervisor about project update"
    })
    assert chat_resp.status_code == 200
    plan_id = chat_resp.json()["action_plan_id"]

    # First approval should succeed
    first_resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": True
    })
    assert first_resp.status_code == 200

    # Second approval attempt must be blocked with HTTP 400
    second_resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": True
    })
    assert second_resp.status_code == 400
    assert "already been executed" in second_resp.json()["detail"]


def test_approval_cannot_execute_rejected(client):
    """Verifies that a rejected action plan cannot subsequently be executed."""
    chat_resp = client.post("/api/chat", json={
        "message": "Send an email to supervisor about cancelled meeting"
    })
    assert chat_resp.status_code == 200
    plan_id = chat_resp.json()["action_plan_id"]

    # Reject first
    reject_resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": False
    })
    assert reject_resp.status_code == 200

    # Attempt to approve rejected plan must be blocked
    approve_resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": True
    })
    assert approve_resp.status_code == 400
    assert "already been rejected" in approve_resp.json()["detail"]


def test_approval_missing_draft_id_rejected(client):
    """Verifies that an email action cannot be executed if draft_id is missing or empty."""
    chat_resp = client.post("/api/chat", json={
        "message": "Send email to colleague about conference"
    })
    assert chat_resp.status_code == 200
    plan_id = chat_resp.json()["action_plan_id"]

    # Try to approve with an edited action that clears draft_id
    resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": True,
        "edited_action": {"draft_id": ""}
    })
    assert resp.status_code == 400
    assert "missing valid draft_id" in resp.json()["detail"]


def test_approval_unauthorized_draft_ownership_rejected(client):
    """Verifies that a user cannot approve/send a draft owned by a different user."""
    from app.tools.gmail import _PENDING_DRAFTS

    # Register a draft owned by another user (e.g. user ID 9999)
    other_user_draft = "draft_other_user_9999"
    _PENDING_DRAFTS[other_user_draft] = {
        "user_id": 9999,
        "to": "hacker@example.com",
        "subject": "Exfiltrated Data",
        "body": "Secret info",
    }

    chat_resp = client.post("/api/chat", json={
        "message": "Send email to student about office hours"
    })
    assert chat_resp.status_code == 200
    plan_id = chat_resp.json()["action_plan_id"]

    # Current user tries to approve sending the other user's draft
    resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": True,
        "edited_action": {"draft_id": other_user_draft}
    })
    assert resp.status_code == 403
    assert "Unauthorized" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_execute_tool_propagates_error_without_wrapping():
    """Verifies execute_tool pre-validates missing required arguments and returns status error."""
    from app.agents.tool_registry import execute_tool

    # Missing required 'to' parameter for create_draft
    res = await execute_tool("create_draft", {"subject": "Test", "body": "Body only"})
    assert res["status"] == "error"
    assert "Missing required parameter" in res["message"]

    # Missing required 'draft_id' parameter for send_email
    send_res = await execute_tool("send_email", {}, bypass_approval=True)
    assert send_res["status"] == "error"
    assert "Missing required parameter" in send_res["message"]


def test_tool_failure_in_approval_records_failed_status(client):
    """Verifies that if a tool fails during approval, plan status transitions to 'failed' and error is reported."""
    chat_resp = client.post("/api/chat", json={
        "message": "Send email to advisor about thesis draft"
    })
    assert chat_resp.status_code == 200
    plan_id = chat_resp.json()["action_plan_id"]

    # Approve with a nonexistent draft ID which causes send_email to fail
    resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": True,
        "edited_action": {"draft_id": "draft_nonexistent_fails_tool_exec"}
    })
    # Should return an error (500 or 400), not success
    assert resp.status_code in (400, 500)
    assert "failed" in resp.json()["detail"].lower() or "does not exist" in resp.json()["detail"].lower()

    # Re-executing the failed plan should now be blocked
    retry_resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": True
    })
    assert retry_resp.status_code == 400
    assert "failed" in retry_resp.json()["detail"].lower()

