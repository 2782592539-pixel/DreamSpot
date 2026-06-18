"""Tests for /api/system routes."""
def test_status_returns_ok(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "mzc"
    assert "timestamp" in data


def test_status_includes_version(client):
    response = client.get("/api/system/status")
    assert response.json()["version"] == "0.1.0"
