import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from psycopg import connect

app = FastAPI(title="CIVIC WATCH", version="0.2.0", description="Read-only demonstration; public submissions disabled.")
ROOT = Path(__file__).resolve().parent

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}

@app.get("/ready")
def ready():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(status_code=503, detail="database not configured")
    try:
        with connect(url, connect_timeout=5) as conn:
            conn.execute("SELECT 1")
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")

@app.get("/incidents")
def incidents():
    return {"items": [], "count": 0, "mode": "read_only", "message": "No live feeds connected"}

@app.get("/demo/incidents")
def demo_incidents():
    return {"mode": "synthetic", "items": [
        {"id": "demo-1", "title": "Example public oversight hearing", "category": "police", "latitude": 36.1627, "longitude": -86.7816, "status": "DEMO ONLY"},
        {"id": "demo-2", "title": "Example immigration policy review", "category": "immigration", "latitude": 36.125, "longitude": -86.79, "status": "DEMO ONLY"},
        {"id": "demo-3", "title": "Example ALPR contract review", "category": "surveillance", "latitude": 36.10, "longitude": -86.75, "status": "DEMO ONLY"},
        {"id": "demo-4", "title": "Example accountability meeting", "category": "police", "latitude": 36.20, "longitude": -86.73, "status": "DEMO ONLY"}
    ]}
