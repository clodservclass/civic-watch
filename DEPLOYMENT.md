# CIVIC WATCH staging deployment

This is a demonstration-only build. No public submission, evidence upload, or live tracking endpoints exist.

1. Review and merge the feature pull request only after GitHub Actions tests pass.
2. In Railway, create a staging service from this repository, root directory `/`, Dockerfile `Dockerfile`.
3. Generate a staging domain and check `/health`, `/docs`, `/demo/incidents`.
4. For database integration, provision a **PostGIS-enabled** PostgreSQL service (plain PostgreSQL does not provide PostGIS). Set `DATABASE_URL` as a Railway private variable reference. Initialize `schema.sql` through a reviewed migration.
5. `/ready` returns 503 until `DATABASE_URL` points to a working database; `/health` checks only process liveness.
6. Do not configure production auto-deploy or paid services without approval.

For local testing: `cp .env.example .env`, set password, `docker compose up --build -d`. Run `pip install -r api/requirements.txt pytest httpx && pytest -q`.
