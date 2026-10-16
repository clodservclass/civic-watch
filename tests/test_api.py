from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json()["version"] == "0.8.0"

def test_dashboard():
    r = client.get("/")
    assert r.status_code == 200
    assert "DEMONSTRATION ONLY" in r.text
    assert "tile.openstreetmap.org" in r.text

def test_mirror():
    r = client.get("/mirror")
    assert r.status_code == 200
    assert "SIMULATION" in r.text
    assert "No real cameras" in r.text

def test_registry():
    r = client.get("/surveillance/registry")
    assert r.status_code == 200
    assert "Verification-first publication" in r.text
    assert "/api/surveillance/programs" in r.text

def test_synthetic_separation():
    data = client.get("/demo/incidents").json()
    assert data["mode"] == "synthetic"
    assert len(data["items"]) == 4
    assert all(x["status"] == "DEMO ONLY" for x in data["items"])

def test_public_api_unconfigured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert client.get("/incidents").json()["items"] == []
    assert client.get("/ready").status_code == 503
    r = client.get("/api/surveillance/programs")
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert client.get("/api/surveillance/programs/00000000-0000-0000-0000-000000000001").status_code == 404

def test_filters_validation():
    assert client.get("/incidents?limit=101").status_code == 422
    assert client.get("/incidents?category=invalid").status_code == 422
    assert client.get("/api/surveillance/programs?limit=101").status_code == 422
    assert client.get("/api/surveillance/programs?offset=-1").status_code == 422
    assert client.get("/api/surveillance/programs?technology=unknown").status_code == 422
    assert client.get("/api/surveillance/programs/not-a-uuid").status_code == 422

def test_no_write_routes():
    assert client.post("/incidents", json={}).status_code == 405
    assert client.post("/evidence", json={}).status_code == 404
    assert client.post("/api/surveillance/programs", json={}).status_code == 405

def test_technology_guides():
    page = client.get("/technology")
    assert page.status_code == 200
    assert "Know the technology" in page.text
    response = client.get("/api/technology-guides")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "educational"
    assert data["count"] >= 6
    assert "alpr" in {guide["slug"] for guide in data["items"]}
    assert all(guide["sources"] for guide in data["items"])

def test_registry_links_to_technology_guides():
    assert 'href="/technology"' in client.get("/surveillance/registry").text

def test_civil_liberties_guides():
    page = client.get("/rights")
    assert page.status_code == 200
    assert "Know your rights" in page.text
    data = client.get("/api/rights-guides").json()
    assert data["mode"] == "educational"
    assert data["count"] >= 6
    assert all(item["sources"] for item in data["items"])

def test_coverage_is_simulation_only():
    page = client.get("/coverage")
    assert page.status_code == 200
    assert "FICTIONAL COVERAGE DEMONSTRATION" in page.text
    assert "no basemap" in page.text
    assert "real-world coordinates" in page.text

def test_registry_links_to_coverage():
    assert 'href="/coverage"' in client.get("/surveillance/registry").text

def test_public_map_empty_by_default():
    page = client.get("/map")
    assert page.status_code == 200
    assert "Public Information Map" in page.text
    for layer in ("closures", "incidents", "historical", "surveillance"):
        assert 'data-layer="' + layer + '"' in page.text
    response = client.get("/api/map/features")
    assert response.status_code == 200
    assert response.json() == {"type": "FeatureCollection", "features": []}

def test_public_map_rejects_unreviewed_data():
    from api.main import validate_public_map
    import pytest
    sample = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "geometry": {"type": "Point", "coordinates": [-86.78, 36.16]},
        "properties": {"layer": "surveillance", "data_status": "verified",
                       "title": "Example", "source_name": "Example",
                       "source_url": "https://example.org/document",
                       "reviewed_at": "2025-01-01T00:00:00Z"}
    }]}
    with pytest.raises(ValueError):
        validate_public_map(sample)
    sample["features"][0]["properties"]["layer"] = "historical"
    with pytest.raises(ValueError):
        validate_public_map(sample)
    sample["features"][0]["properties"]["layer"] = "incidents"
    sample["features"][0]["properties"]["data_status"] = "draft"
    with pytest.raises(ValueError):
        validate_public_map(sample)
