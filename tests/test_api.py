from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)

def test_health():
    assert client.get("/health").json()["version"] == "0.3.0"

def test_dashboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "DEMONSTRATION ONLY" in response.text
    assert "tile.openstreetmap.org" in response.text

def test_synthetic_separation():
    result = client.get("/demo/incidents").json()
    assert result["mode"] == "synthetic"
    assert len(result["items"]) == 4
    assert all(item["status"] == "DEMO ONLY" for item in result["items"])

def test_public_api_unconfigured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert client.get("/incidents").json()["items"] == []
    assert client.get("/incidents/00000000-0000-0000-0000-000000000001").status_code == 404
    assert client.get("/ready").status_code == 503

def test_filters_validation():
    assert client.get("/incidents?limit=101").status_code == 422
    assert client.get("/incidents?offset=-1").status_code == 422
    assert client.get("/incidents?category=invalid").status_code == 422
    assert client.get("/incidents/not-a-uuid").status_code == 422

def test_no_write_routes():
    assert client.post("/incidents", json={}).status_code == 405
    assert client.post("/evidence", json={}).status_code == 404
