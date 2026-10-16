import os
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from psycopg import connect
from psycopg.rows import dict_row

app = FastAPI(title="CIVIC WATCH", version="0.3.0", description="Read-only historical records; submissions and evidence uploads disabled.")
ROOT = Path(__file__).resolve().parent

def db_url():
    return os.getenv("DATABASE_URL")

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.3.0"}

@app.get("/ready")
def ready():
    url = db_url()
    if not url:
        raise HTTPException(status_code=503, detail="database not configured")
    try:
        with connect(url, connect_timeout=5) as conn:
            conn.execute("SELECT 1 FROM schema_migrations WHERE version = '0001'")
        return {"status": "ready", "database": "connected", "schema": "0001"}
    except Exception:
        raise HTTPException(status_code=503, detail="database or schema unavailable")

# No public record is returned unless human-approved, published and non-sensitive.
PUBLIC_SQL = """
SELECT id::text AS id, title, description, category, occurred_at, published_at,
       verification_status, public_location_label, source_count
FROM public_incidents
WHERE (%s::text IS NULL OR category = %s)
ORDER BY published_at DESC, id DESC
LIMIT %s OFFSET %s
"""

@app.get("/incidents")
def incidents(category: Literal["police", "immigration", "surveillance", "other"] | None = None,
              limit: int = Query(25, ge=1, le=100),
              offset: int = Query(0, ge=0, le=10000)):
    if not db_url():
        return {"items": [], "count": 0, "mode": "read_only", "message": "Database not configured; no published records"}
    try:
        with connect(db_url(), connect_timeout=5, row_factory=dict_row) as conn:
            rows = conn.execute(PUBLIC_SQL, (category, category, limit, offset)).fetchall()
        return {"items": rows, "count": len(rows), "mode": "read_only", "limit": limit, "offset": offset}
    except Exception:
        raise HTTPException(status_code=503, detail="Public records database unavailable")

@app.get("/incidents/{incident_id}")
def incident_detail(incident_id: UUID):
    if not db_url():
        raise HTTPException(status_code=404, detail="Record not found")
    try:
        with connect(db_url(), connect_timeout=5, row_factory=dict_row) as conn:
            record = conn.execute(
                """SELECT id::text AS id, title, description, category, occurred_at,
                          published_at, verification_status, public_location_label, source_count
                   FROM public_incidents WHERE id = %s""", (incident_id,)).fetchone()
            if record is None:
                raise HTTPException(status_code=404, detail="Record not found")
            sources = conn.execute(
                """SELECT source_type, source_title, source_url, published_at
                   FROM public_sources WHERE incident_id = %s ORDER BY published_at DESC NULLS LAST""",
                (incident_id,)).fetchall()
        return {"record": record, "sources": sources}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Public records database unavailable")

@app.get("/demo/incidents")
def demo_incidents():
    return {"mode": "synthetic", "items": [
        {"id": "demo-1", "title": "Example public oversight hearing", "category": "police", "latitude": 36.1627, "longitude": -86.7816, "status": "DEMO ONLY"},
        {"id": "demo-2", "title": "Example immigration policy review", "category": "immigration", "latitude": 36.125, "longitude": -86.79, "status": "DEMO ONLY"},
        {"id": "demo-3", "title": "Example ALPR contract review", "category": "surveillance", "latitude": 36.10, "longitude": -86.75, "status": "DEMO ONLY"},
        {"id": "demo-4", "title": "Example accountability meeting", "category": "police", "latitude": 36.20, "longitude": -86.73, "status": "DEMO ONLY"}
    ]}
