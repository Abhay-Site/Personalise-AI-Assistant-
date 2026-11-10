"""
tests/test_db.py — Database initialization and CRUD tests
"""

from app.database import crud


def test_db_creates_user(client):
    """
    Calling /api/auth/me should auto-create the mock user in the database.
    """
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "demo@assistant.dev"
    assert data["name"] == "Demo User"
    assert "id" in data


def test_auth_status(client):
    """Auth status endpoint should return configuration flags."""
    response = client.get("/api/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert "gemini_configured" in data
    assert "google_oauth_configured" in data
    assert data["mock_mode"] is True


def test_memory_crud(client):
    """Create, list, update, and delete a memory entry."""
    # Create
    create_resp = client.post("/api/memory", json={
        "key": "preferred_meeting_time",
        "value": "11 AM to 4 PM",
        "category": "scheduling",
    })
    assert create_resp.status_code == 201
    memory_id = create_resp.json()["id"]

    # List — should include the new memory
    list_resp = client.get("/api/memory")
    assert list_resp.status_code == 200
    keys = [m["key"] for m in list_resp.json()]
    assert "preferred_meeting_time" in keys

    # Update — disable the memory
    update_resp = client.put(f"/api/memory/{memory_id}", json={"enabled": False})
    assert update_resp.status_code == 200
    assert update_resp.json()["enabled"] is False

    # Delete
    delete_resp = client.delete(f"/api/memory/{memory_id}")
    assert delete_resp.status_code == 204


def test_delete_nonexistent_memory(client):
    """Deleting a memory that doesn't exist should return 404."""
    response = client.delete("/api/memory/999999")
    assert response.status_code == 404
