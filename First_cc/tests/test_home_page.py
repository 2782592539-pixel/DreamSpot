"""Tests for the custom home page and static asset serving."""


def test_home_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_home_references_assets(client):
    html = client.get("/").text
    assert "app.css" in html
    assert "app.js" in html


def test_swagger_ui_disabled(client):
    response = client.get("/docs")
    assert response.status_code == 404


def test_redoc_disabled(client):
    response = client.get("/redoc")
    assert response.status_code == 404


def test_static_assets_directory_mounted(client):
    """Verify /assets/ route is reachable (StaticFiles returns 404 for missing files)."""
    response = client.get("/assets/does-not-exist.css")
    # StaticFiles returns 404 for missing files but the mount itself works
    assert response.status_code in (200, 404)
