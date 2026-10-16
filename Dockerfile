FROM python:3.12-slim
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser
COPY api/main.py api/index.html api/mirror.html api/registry.html api/technology.html api/technology_guides.json api/rights.html api/rights_guides.json api/coverage.html api/public_map.html api/public_map_records.geojson ./
USER appuser
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
