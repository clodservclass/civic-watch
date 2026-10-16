from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)
def test_health():
    assert client.get("/health").json()["version"] == "0.2.0"
def test_dashboard():
    r=client.get("/")
    assert r.status_code == 200
    assert "DEMONSTRATION ONLY" in r.text
    assert "tile.openstreetmap.org" in r.text
def test_demo():
    data=client.get("/demo/incidents").json()
    assert data["mode"] == "synthetic"
    assert {x["category"] for x in data["items"]} == {"police","immigration","surveillance"}
    assert all(x["status"]=="DEMO ONLY" for x in data["items"])
def test_read_only():
    assert client.get("/incidents").json()["items"] == []
    assert client.post("/incidents",json={}).status_code == 405
    assert client.post("/evidence",json={}).status_code == 404
def test_ready_unconfigured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL",raising=False)
    assert client.get("/ready").status_code == 503
