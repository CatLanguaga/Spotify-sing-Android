# Deploy — Docker / Coolify

Single-container build: a multi-stage `Dockerfile` builds the React SPA, then a
Python 3.11 image serves both the static frontend (`/`) and the API (`/api`) with
`ffmpeg` included. One service, one port (`8000`).

## Local (3 steps)

```bash
cp .env.example .env          # 1. fill in SPOTIFY_CLIENT_ID / SECRET
docker compose build          # 2. build image
docker compose up -d          # 3. run -> http://localhost:8000
```

Logs: `docker compose logs -f`. Stop: `docker compose down`.

## Coolify

1. **New Resource → Application → Docker / Dockerfile**, point it at this repo
   (branch `page-test` or your release branch). Coolify auto-detects the root
   `Dockerfile`.
2. **Environment variables** (Coolify UI):
   - `SPOTIFY_CLIENT_ID` — required
   - `SPOTIFY_CLIENT_SECRET` — required
   - optional: `MAX_TRACKS_PER_REQUEST` (default 50),
     `SPOTIFY_MAX_CONCURRENT_DOWNLOADS` (default 3)
   - leave `DOWNLOAD_DIR` / `SPOTIFY_QUEUE_FILE` at their image defaults
     (`/app/downloads`, `/app/data/queue.json`).
3. **Port**: set the exposed port to `8000`. Coolify terminates SSL and proxies
   to it; the SPA uses a relative `/api`, so it works under any domain/scheme.
4. **Persistent storage** (optional but recommended): mount volumes for
   `/app/downloads` and `/app/data`.
5. **Health check**: `GET /health` returns `{"status":"ok"}`. The image also
   ships a Docker `HEALTHCHECK`.

Deploy. Done.

## Credentials model

Single-tenant: `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` come from env vars and
override anything in `config.json`. The in-app Settings screen still works for
local dev (no env vars set), but in the container the env values win.

## Notes

- `ffmpeg` is installed in the runtime image — required for mp3/m4a/opus transcode.
- Downloaded files land in `/app/downloads` and are auto-cleaned after serving.
- `pywebview` and `google-api-python-client` are excluded from the container
  (`requirements-docker.txt`) — desktop/unused deps.
