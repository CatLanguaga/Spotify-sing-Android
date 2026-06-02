# syntax=docker/dockerfile:1

# ---------- Stage 1: build the React frontend ----------
FROM node:20-slim AS frontend
WORKDIR /app/gui/frontend

# Install deps first (cached unless lockfile changes)
COPY gui/frontend/package.json gui/frontend/package-lock.json ./
RUN npm ci

# Build the SPA -> gui/frontend/dist
COPY gui/frontend/ ./
RUN npm run build


# ---------- Stage 2: Python backend serving the SPA ----------
FROM python:3.11-slim AS runtime

# ffmpeg is required to transcode pytubefix audio into mp3/m4a/opus.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (server-only subset)
COPY requirements-docker.txt ./
RUN pip install --no-cache-dir -r requirements-docker.txt

# Application code (gui/ and gui/backend/ are implicit namespace packages — no __init__.py)
COPY src/ ./src/
COPY gui/backend/ ./gui/backend/

# Built frontend from stage 1 (main.py mounts this dir at "/")
COPY --from=frontend /app/gui/frontend/dist ./gui/frontend/dist

ENV SPOTIFY_SYNC_ROOT=/app \
    DOWNLOAD_DIR=/app/downloads \
    SPOTIFY_QUEUE_FILE=/app/data/queue.json \
    PYTHONUNBUFFERED=1

# Volumes: downloaded audio (ephemeral, auto-cleaned) + queue state
RUN mkdir -p /app/downloads /app/data
VOLUME ["/app/downloads", "/app/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# reload disabled in prod; bind 0.0.0.0 so Coolify's proxy can reach it.
CMD ["uvicorn", "gui.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
