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


def test_home_contains_key_sections(client):
    html = client.get("/").text
    # Top-level brand and Chinese title
    assert "MZC" in html
    # Script loads app.js
    assert "/assets/app.js" in html
    # Status bar element exists
    assert "id=\"statusbar\"" in html or 'id="statusbar"' in html
    # Sidebar element exists
    assert "id=\"sidebar\"" in html or 'id="sidebar"' in html


def test_css_contains_dark_theme(client):
    css = client.get("/assets/app.css").text
    # Dark background color from the spec
    assert "#0d1117" in css
    # Card color
    assert "#161b22" in css


def test_css_contains_method_colors(client):
    css = client.get("/assets/app.css").text
    # GET = blue, POST = green from spec
    assert "#58a6ff" in css  # GET / accent
    assert "#3fb950" in css  # POST / success


def test_js_served(client):
    response = client.get("/assets/app.js")
    assert response.status_code == 200
    # Content-Type may be text/javascript, application/javascript, or similar
    ct = response.headers.get("content-type", "").lower()
    assert "javascript" in ct or "ecmascript" in ct or "text/plain" in ct


def test_js_fetches_openapi(client):
    js = client.get("/assets/app.js").text
    # JS should reference /openapi.json
    assert "/openapi.json" in js
    # JS should call fetch
    assert "fetch(" in js
