import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from psycopg import connect

app = FastAPI(title="CIVIC WATCH", version="0.1.0", description="Read-only demonstration. Submissions disabled.")
ROOT = Path(__file__).resolve().parent

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    try:
        with connect(os.environ["DATABASE_URL"], connect_timeout=5) as conn:
            conn.execute("SELECT 1")
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")

@app.get("/incidents")
def incidents():
    return {"items": [], "count": 0, "mode": "demo", "message": "No live feeds connected"}

@app.get("/demo/incidents")
def demo_incidents():
    return {"mode": "synthetic", "items": [
        {"id": "demo-1", "title": "Fictional road closure", "latitude": 36.1627, "longitude": -86.7816, "status": "DEMO ONLY"},
        {"id": "demo-2", "title": "Fictional safety advisory", "latitude": 36.107, "longitude": -86.775, "status": "DEMO ONLY"}
    ]}
