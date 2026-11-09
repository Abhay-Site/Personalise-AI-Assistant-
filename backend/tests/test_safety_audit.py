"""
tests/test_safety_audit.py — Tests for Safety, Secret Sanitization, and Advanced Audit Filtering
"""

from app.services.audit_service import log_action, sanitize_summary
from tests.conftest import TestSessionLocal


def test_sanitize_summary_redacts_keys_and_passwords():
    """Verifies that API keys, passwords, and bearer tokens are masked."""
    raw_key = "Connecting with key AIzaSyD987654321012345678901234567890a for auth"
    clean_key = sanitize_summary(raw_key)
    assert "[REDACTED_API_KEY]" in clean_key
    assert "AIzaSyD" not in clean_key

    raw_pwd = "User login attempt with password: super_secret_pass_123"
    clean_pwd = sanitize_summary(raw_pwd)
    assert "[REDACTED_SECRET]" in clean_pwd
    assert "super_secret_pass_123" not in clean_pwd


def test_audit_log_persists_sanitized(client):
    """Verifies log_action redacts secrets when persisting to the database."""
    db = TestSessionLocal()

    log_action(
        db=db,
        user_id=1,
        tool_name="test_tool",
        service="system",
        action_type="read",
        status="success",
        input_summary="Input with password='my_confidential_password'",
        result_summary="Output ok",
    )
    db.close()

    resp = client.get("/api/audit?service=system")
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) > 0
    # Find our logged action
    matched = [l for l in logs if l.get("tool_name") == "test_tool"]
    assert len(matched) > 0
    latest = matched[0]
    assert "my_confidential_password" not in (latest.get("input_summary") or "")
    assert "[REDACTED_SECRET]" in (latest.get("input_summary") or "")


def test_audit_query_filtering(client):
    """Tests filtering audit logs by service, status, approval_status, and search keyword."""
    # 1. Filter by service
    gmail_resp = client.get("/api/audit?service=gmail")
    assert gmail_resp.status_code == 200
    for l in gmail_resp.json():
        assert l["service"] == "gmail"

    # 2. Filter by status
    success_resp = client.get("/api/audit?status=success")
    assert success_resp.status_code == 200
    for l in success_resp.json():
        assert l["status"] == "success"

    # 3. Filter by search query
    search_resp = client.get("/api/audit?q=test")
    assert search_resp.status_code == 200


def test_approval_with_edited_parameters(client):
    """
    Verifies that when a user edits parameters in the approval modal,
    the approved action executes with the user's modifications.
    """
    # 1. Trigger action plan requiring approval
    chat_resp = client.post("/api/chat", json={
        "message": "Send an email to the lab instructor regarding project submission"
    })
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["requires_approval"] is True
    plan_id = data["action_plan_id"]

    # 2. Approve with edited parameters
    edited_payload = {
        "to": "custom.recipient@university.edu",
        "subject": "Custom Lab Submission Title",
        "body": "Updated message body directly from approval modal.",
    }

    approval_resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": True,
        "edited_action": edited_payload,
    })
    assert approval_resp.status_code == 200
    res = approval_resp.json()
    assert res["status"] == "executed"
    assert res["approved"] is True
