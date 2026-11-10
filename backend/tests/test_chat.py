"""
tests/test_chat.py — Tests for the /api/chat endpoint
"""


def test_chat_creates_conversation(client):
    """
    Sending a message without a conversation_id should auto-create one.
    """
    response = client.post("/api/chat", json={"message": "Hello Personal AI Assistant!"})
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert data["conversation_id"] > 0
    assert "reply" in data
    assert len(data["reply"]) > 0


def test_chat_returns_trace(client):
    """Response should always include an execution trace."""
    response = client.post("/api/chat", json={"message": "What can you do?"})
    assert response.status_code == 200
    data = response.json()
    assert "trace" in data
    assert isinstance(data["trace"], list)
    assert len(data["trace"]) > 0


def test_chat_generates_action_plan_for_complex_request(client):
    """
    A request mentioning calendar/drive/email should generate an action plan.
    """
    response = client.post("/api/chat", json={
        "message": "Find tomorrow's project meeting and send the report by email."
    })
    assert response.status_code == 200
    data = response.json()
    # This message contains calendar + email signals → plan should be generated
    assert data["action_plan"] is not None
    assert len(data["action_plan"]["steps"]) > 0


def test_chat_sensitive_action_requires_approval(client):
    """
    A message containing 'send email' must flag requires_approval=True.
    """
    response = client.post("/api/chat", json={
        "message": "Send an email to my professor about the assignment deadline."
    })
    assert response.status_code == 200
    data = response.json()
    assert data["requires_approval"] is True
    assert data["approval_action"] is not None


def test_chat_continues_existing_conversation(client):
    """Sending a message with a valid conversation_id should reuse it."""
    # Start conversation
    first = client.post("/api/chat", json={"message": "Start a conversation"})
    conversation_id = first.json()["conversation_id"]

    # Continue it
    second = client.post("/api/chat", json={
        "message": "Follow up message",
        "conversation_id": conversation_id,
    })
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id


def test_chat_invalid_conversation_id(client):
    """Referencing a non-existent conversation should return 404."""
    response = client.post("/api/chat", json={
        "message": "Hello",
        "conversation_id": 999999,
    })
    assert response.status_code == 404


def test_chat_empty_message_rejected(client):
    """An empty message should be rejected by Pydantic validation."""
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422  # Unprocessable Entity


def test_audit_log_created_after_chat(client):
    """After a chat message, at least one audit log should exist."""
    client.post("/api/chat", json={"message": "Test audit log creation"})
    audit_response = client.get("/api/audit")
    assert audit_response.status_code == 200
    assert len(audit_response.json()) > 0


def test_chat_returns_integration_status(client):
    """Chat endpoint must report integration_status, model_name, and is_fallback."""
    response = client.post("/api/chat", json={"message": "Hello Personal AI Assistant!"})
    assert response.status_code == 200
    data = response.json()
    assert "integration_status" in data
    assert data["integration_status"] in ["connected", "fallback", "demo"]
    assert "is_fallback" in data
    assert isinstance(data["is_fallback"], bool)
