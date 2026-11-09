"""
tests/test_google_integration.py — Tests for Google Services, OAuth and Tools
"""

import pytest
from app.tools import gmail, calendar, drive


def test_auth_me_endpoint(client):
    """Verifies that /api/auth/me returns user profile and accurate service statuses."""
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "google_connected" in data
    assert "services" in data
    # When real Google OAuth is not connected, services must accurately report False (not pretend to be connected)
    assert data["google_connected"] is False
    assert data["services"]["gmail"] is False
    assert data["services"]["calendar"] is False
    assert data["services"]["drive"] is False
    assert data["mode"] == "demo"


def test_auth_status_distinguishes_demo_and_reports_missing_config(client):
    """Verifies that /api/auth/status identifies demo mode and missing keys without exposing secrets."""
    response = client.get("/api/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert "google_connected" in data
    assert data["google_connected"] is False
    assert data["mock_mode"] is True
    assert "missing_config" in data


def test_simulated_connect_never_claims_real_google(client):
    """Verifies that simulate-connect clearly indicates demo mode and never claims real Google connection."""
    response = client.post("/api/auth/simulate-connect")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "demo"
    assert data["google_connected"] is False
    assert data["simulated_connected"] is True

    # Check /me after simulation
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["google_connected"] is False
    assert me_data["simulated_connected"] is True
    assert me_data["mode"] == "demo"


def test_auth_login_redirect(client):
    """Verifies that /api/auth/login initiates an OAuth redirect."""
    response = client.get("/api/auth/login", follow_redirects=False)
    # Must return an HTTP redirect (302 or 307)
    assert response.status_code in [302, 307]
    assert "location" in response.headers


def test_auth_disconnect(client):
    """Verifies that disconnecting Google succeeds without error."""
    response = client.post("/api/auth/disconnect")
    assert response.status_code == 200
    assert response.json()["status"] == "disconnected"


@pytest.mark.asyncio
async def test_gmail_tools_standalone():
    """Verifies Gmail tools return structured, valid responses."""
    # 1. Search
    search_res = await gmail.search_emails(query="meeting")
    assert "messages" in search_res
    assert search_res["status"] in ["connected", "demo"]

    # 2. Create Draft
    draft_res = await gmail.create_draft(to="alice@orbit180.dev", subject="Test", body="Hello")
    assert "draft_id" in draft_res
    assert draft_res["status"] in ["connected", "demo"]
    created_draft_id = draft_res["draft_id"]

    # 3. Send Email with the created draft
    send_res = await gmail.send_email(draft_id=created_draft_id)
    assert "message" in send_res
    assert send_res["status"] in ["connected", "demo"]

    # 4. Refuse sending empty draft ID
    empty_send = await gmail.send_email(draft_id="")
    assert empty_send["status"] == "error"

    # 5. Refuse sending nonexistent draft ID
    nonexistent_send = await gmail.send_email(draft_id="draft_nonexistent_xyz_999")
    assert nonexistent_send["status"] == "error"


@pytest.mark.asyncio
async def test_calendar_tools_standalone():
    """Verifies Calendar tools return structured, valid responses."""
    # 1. List events
    events_res = await calendar.list_events(time_min="2026-09-01T00:00:00Z", time_max="2026-09-30T23:59:59Z")
    assert "events" in events_res
    assert events_res["status"] in ["connected", "demo"]

    # 2. Find free time
    free_res = await calendar.find_free_time(date="2026-09-28")
    assert "free_slots" in free_res

    # 3. Create event
    create_res = await calendar.create_event(title="Study Session", start_time="", end_time="")
    assert "event_id" in create_res


@pytest.mark.asyncio
async def test_drive_tools_standalone():
    """Verifies Drive tools return structured, valid responses."""
    # 1. Search files
    files_res = await drive.search_files(query="report")
    assert "files" in files_res
    assert files_res["status"] in ["connected", "demo"]

    # 2. Metadata
    meta_res = await drive.get_file_metadata(file_id="mock_file_001")
    assert "metadata" in meta_res

    # 3. Content
    content_res = await drive.get_file_content(file_id="mock_file_001")
    assert "content" in content_res
