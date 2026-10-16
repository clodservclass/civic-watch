import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import os
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from psycopg import connect
from psycopg.rows import dict_row

app = FastAPI(title="CIVIC WATCH", version="0.9.0", description="Read-only historical records; submissions and evidence uploads disabled.")
ROOT = Path(__file__).resolve().parent

def db_url():
    return os.getenv("DATABASE_URL")

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.9.0"}

@app.get("/ready")
def ready():
    url = db_url()
    if not url:
        raise HTTPException(status_code=503, detail="database not configured")
    try:
        with connect(url, connect_timeout=5) as conn:
            versions = {row[0] for row in conn.execute("SELECT version FROM schema_migrations WHERE version IN ('0001','0002')")}
            if versions != {'0001', '0002'}:
                raise ValueError('required migrations missing')
        return {"status": "ready", "database": "connected", "schema": "0002"}
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

@app.get("/mirror", include_in_schema=False)
def mirror():
    return FileResponse(ROOT / "mirror.html")

@app.get("/surveillance/registry", include_in_schema=False)
def surveillance_registry():
    return FileResponse(ROOT / "registry.html")

# The runtime DB account must only have SELECT permissions on public views.
# Never query surveillance_programs or surveillance_sources directly in public endpoints.
@app.get("/api/surveillance/programs")
def surveillance_programs(
    q: str | None = Query(None, max_length=120),
    technology: Literal["alpr", "cctv", "facial_recognition", "drones", "analytics", "other"] | None = None,
    jurisdiction: str | None = Query(None, max_length=100),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
):
    if not db_url():
        return {"items": [], "count": 0, "mode": "read_only", "message": "Database not configured; no verified registry records"}
    search = "%" + (q or "").strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    try:
        with connect(db_url(), connect_timeout=5, row_factory=dict_row) as conn:
            rows = conn.execute(
                """SELECT id::text AS id, agency_name, program_name, technology, jurisdiction,
                          vendor_name, description, retention_policy, sharing_policy,
                          contract_amount_usd, published_at, source_count
                   FROM public_surveillance_programs
                   WHERE (%s::text IS NULL OR technology = %s)
                     AND (%s::text IS NULL OR jurisdiction ILIKE ('%%' || %s || '%%'))
                     AND (%s::text IS NULL OR agency_name ILIKE %s ESCAPE '\\'
                          OR program_name ILIKE %s ESCAPE '\\'
                          OR COALESCE(vendor_name,'') ILIKE %s ESCAPE '\\'
                          OR jurisdiction ILIKE %s ESCAPE '\\')
                   ORDER BY published_at DESC, id DESC LIMIT %s OFFSET %s""",
                (technology, technology, jurisdiction, jurisdiction, q, search, search, search, search, limit, offset),
            ).fetchall()
        return {"items": rows, "count": len(rows), "mode": "read_only", "limit": limit, "offset": offset}
    except Exception:
        raise HTTPException(status_code=503, detail="Surveillance registry database unavailable")

@app.get("/api/surveillance/programs/{program_id}")
def surveillance_program_detail(program_id: UUID):
    if not db_url():
        raise HTTPException(status_code=404, detail="Program not found")
    try:
        with connect(db_url(), connect_timeout=5, row_factory=dict_row) as conn:
            program = conn.execute(
                """SELECT id::text AS id, agency_name, program_name, technology, jurisdiction,
                          vendor_name, description, retention_policy, sharing_policy,
                          contract_amount_usd, published_at, source_count
                   FROM public_surveillance_programs WHERE id = %s""", (program_id,),
            ).fetchone()
            if program is None:
                raise HTTPException(status_code=404, detail="Program not found")
            sources = conn.execute(
                """SELECT source_title, source_url, source_type, document_date
                   FROM public_surveillance_sources WHERE program_id = %s
                   ORDER BY document_date DESC NULLS LAST, source_title""", (program_id,),
            ).fetchall()
        return {"program": program, "sources": sources}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Surveillance registry database unavailable")

@app.get("/technology", include_in_schema=False)
def technology_guide_page():
    return FileResponse(ROOT / "technology.html")

@app.get("/api/technology-guides")
def technology_guides():
    with (ROOT / "technology_guides.json").open(encoding="utf-8") as stream:
        items = json.load(stream)
    return {"items": items, "count": len(items), "mode": "educational"}

@app.get("/rights", include_in_schema=False)
def rights_page():
    return FileResponse(ROOT / "rights.html")

@app.get("/api/rights-guides")
def rights_guides():
    with (ROOT / "rights_guides.json").open(encoding="utf-8") as stream:
        items = json.load(stream)
    return {"items": items, "count": len(items), "mode": "educational"}

@app.get("/coverage", include_in_schema=False)
def coverage_lab():
    return FileResponse(ROOT / "coverage.html")

def city_directory():
    with (ROOT / "cities.json").open(encoding="utf-8") as stream:
        return json.load(stream)["cities"]

@app.get("/api/cities")
def cities(q: str = Query("", max_length=100)):
    needle = q.casefold().strip()
    items = [c for c in city_directory() if needle in (c["name"] + " " + c["state"] + " " + c["id"]).casefold()]
    return {"items": items[:100], "count": len(items), "coverage_note": "City listings do not imply data availability"}

MAP_LAYERS = {"closures", "incidents", "historical", "surveillance"}

def validate_public_map(collection):
    if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection" or not isinstance(collection.get("features"), list):
        raise ValueError("invalid map collection")
    if len(collection["features"]) > 500:
        raise ValueError("map record limit exceeded")
    now = datetime.now(timezone.utc)
    for feature in collection["features"]:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("invalid map feature")
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            raise ValueError("invalid feature data")
        if properties.get("city_id") not in {c["id"] for c in city_directory()}:
            raise ValueError("unknown city identifier")
        layer = properties.get("layer")
        if layer not in MAP_LAYERS or properties.get("data_status") != "verified":
            raise ValueError("unverified map record")
        for key in ("title", "source_name"):
            if not isinstance(properties.get(key), str) or not properties[key].strip() or len(properties[key]) > 200:
                raise ValueError("missing map attribution")
        url = properties.get("source_url")
        if not isinstance(url, str) or urlparse(url).scheme != "https" or not urlparse(url).hostname:
            raise ValueError("invalid source URL")
        reviewed = properties.get("reviewed_at")
        try:
            reviewed_at = datetime.fromisoformat(reviewed.replace("Z", "+00:00"))
            if reviewed_at.tzinfo is None or reviewed_at > now:
                raise ValueError()
        except (AttributeError, ValueError):
            raise ValueError("invalid review timestamp")
        shape = geometry.get("type")
        if shape not in {"Point", "Polygon", "MultiPolygon"}:
            raise ValueError("unsupported geometry")
        if layer == "surveillance" and shape not in {"Polygon", "MultiPolygon"}:
            raise ValueError("surveillance areas must be generalized")
        if layer == "historical":
            if shape not in {"Polygon", "MultiPolygon"} or properties.get("aggregation_count", 0) < 5:
                raise ValueError("historical activity must be aggregated into areas")
            observed = properties.get("observed_at")
            try:
                observed_at = datetime.fromisoformat(observed.replace("Z", "+00:00"))
                if observed_at.tzinfo is None or observed_at > now - timedelta(days=7):
                    raise ValueError()
            except (AttributeError, ValueError):
                raise ValueError("historical records must be delayed")
        # GeoJSON coordinates must be finite lon/lat pairs. Keep geographic
        # validation conservative; public publication remains human reviewed.
        def valid_coords(node):
            if isinstance(node, list) and len(node) >= 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in node[:2]) and all(not isinstance(v, (dict, list)) for v in node[:2]):
                from math import isfinite
                return len(node) == 2 and all(isfinite(v) for v in node) and -180 <= node[0] <= 180 and -90 <= node[1] <= 90
            return isinstance(node, list) and bool(node) and all(valid_coords(part) for part in node)
        if not valid_coords(geometry.get("coordinates")):
            raise ValueError("invalid map coordinates")
    return collection

@app.get("/map", include_in_schema=False)
def public_map_page():
    return FileResponse(ROOT / "public_map.html")

@app.get("/api/map/features")
def public_map_features(city: str = Query("nashville-tn", max_length=100)):
    try:
        with (ROOT / "public_map_records.geojson").open(encoding="utf-8") as stream:
            collection = validate_public_map(json.load(stream))
        if city not in {c["id"] for c in city_directory()}:
            raise HTTPException(status_code=404, detail="Unknown city")
        collection["features"] = [f for f in collection["features"] if f["properties"]["city_id"] == city]
        return collection
    except (OSError, ValueError, TypeError):
        raise HTTPException(status_code=503, detail="Reviewed map dataset unavailable")
