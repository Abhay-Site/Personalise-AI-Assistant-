"""
tests/test_differentiation.py — Tests for Privacy Shield, Conflict Auditor, and Morning Briefing
"""

import pytest
from app.services.privacy_shield import redact_pii
from app.services.conflict_service import detect_schedule_conflicts


def test_privacy_shield_redactions():
    """Verifies that Privacy Shield redacts phones, credit cards, passwords, and tokens."""
    # 1. Phone number
    phone_text = "Please reach me at +1 (555) 234-5678 regarding the submission."
    clean_phone, entities = redact_pii(phone_text)
    assert "[REDACTED_PHONE]" in clean_phone
    assert "555" not in clean_phone
    assert len(entities) > 0

    # 2. Credit card
    card_text = "Account billing card: 4111-2222-3333-4444 on file"
    clean_card, _ = redact_pii(card_text)
    assert "[REDACTED_CARD_NUMBER]" in clean_card
    assert "4111" not in clean_card

    # 3. Password
    pwd_text = "Access credentials: password='SecretStudentKey123'"
    clean_pwd, _ = redact_pii(pwd_text)
    assert "[REDACTED_SECRET]" in clean_pwd
    assert "SecretStudentKey123" not in clean_pwd


def test_conflict_auditor():
    """Verifies that overlapping calendar commitments are flagged as schedule conflicts."""
    colliding_events = [
        {"id": "e1", "summary": "Project Review Meeting", "start": "Tomorrow, 2:00 PM", "end": "Tomorrow, 3:00 PM"},
        {"id": "e2", "summary": "AI Lab Session", "start": "Tomorrow, 2:00 PM", "end": "Tomorrow, 4:00 PM"},
    ]
    conflicts = detect_schedule_conflicts(colliding_events)
    assert len(conflicts) > 0
    assert conflicts[0]["severity"] == "high"
    assert "Project Review Meeting" in conflicts[0]["event_a"]
    assert "AI Lab Session" in conflicts[0]["event_b"]


def test_morning_briefing_api(client):
    """Verifies that /api/briefing returns the daily proactive briefing."""
    response = client.get("/api/briefing")
    assert response.status_code == 200
    data = response.json()
    assert "greeting" in data
    assert "ai_summary" in data
    assert "events" in data
    assert "important_emails" in data
    assert "recommended_files" in data
    assert "stats" in data


def test_schedule_conflicts_api(client):
    """Verifies that /api/briefing/conflicts returns detected conflicts."""
    response = client.get("/api/briefing/conflicts")
    assert response.status_code == 200
    data = response.json()
    assert "conflicts" in data
    assert "count" in data
