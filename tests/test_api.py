from fastapi.testclient import TestClient
from api.main import app
client = TestClient(app)

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_landing():
    response = client.get("/")
    assert response.status_code == 200
    assert "DEMONSTRATION ONLY" in response.text

def test_live_feed_disabled():
    assert client.get("/incidents").json()["items"] == []

def test_demo_labeled():
    assert all("DEMO" in x["status"] for x in client.get("/demo/incidents").json()["items"])

def test_write_endpoints_disabled():
    assert client.post("/incidents", json={}).status_code == 405
    assert client.post("/evidence", json={}).status_code == 404
