"""
tests/test_health.py — Tests for the /health endpoint
"""


def test_health_returns_200(client):
    """Health endpoint must return HTTP 200 and status=ok."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_structure(client):
    """Health endpoint must return the expected JSON structure."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ORBIT 180"
    assert "gemini_configured" in data
    assert "google_oauth_configured" in data


def test_health_not_post(client):
    """Health endpoint should not accept POST requests."""
    response = client.post("/health")
    assert response.status_code == 405  # Method Not Allowed
