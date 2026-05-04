FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5000 \
    FLASK_DEBUG=0 \
    OPENPARTSLIBRARY_DATA_DIR=/app/data \
    GUNICORN_WORKERS=2 \
    GUNICORN_TIMEOUT=120 \
    FREECAD_3MF_EXPORT_COMMAND="" \
    BLENDER_THUMBNAIL_COMMAND=""

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"5000\")}/', timeout=3).read()" || exit 1

CMD gunicorn \
    --bind "${HOST}:${PORT}" \
    --workers "${GUNICORN_WORKERS}" \
    --timeout "${GUNICORN_TIMEOUT}" \
    --access-logfile - \
    --error-logfile - \
    app:app
