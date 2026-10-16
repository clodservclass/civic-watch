from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)

def test_health():
    assert client.get("/health").json()["version"] == "0.4.0"

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
    assert "Reveal first detection" in r.text

def test_registry():
    r = client.get("/surveillance/registry")
    assert r.status_code == 200
    assert "no verified entries published" in r.text
    assert "Source links" in r.text

def test_synthetic_separation():
    data = client.get("/demo/incidents").json()
    assert data["mode"] == "synthetic"
    assert len(data["items"]) == 4
    assert all(x["status"] == "DEMO ONLY" for x in data["items"])

def test_public_api_unconfigured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert client.get("/incidents").json()["items"] == []
    assert client.get("/ready").status_code == 503

def test_filters_validation():
    assert client.get("/incidents?limit=101").status_code == 422
    assert client.get("/incidents?category=invalid").status_code == 422

def test_no_write_routes():
    assert client.post("/incidents", json={}).status_code == 405
    assert client.post("/evidence", json={}).status_code == 404
