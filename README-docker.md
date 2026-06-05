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

Two paths, both supported:

1. **Env-driven** (CI/staging): set `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`
   in the Coolify UI. These always win over the on-disk config.
2. **Admin-managed** (recommended for prod): leave the Spotify envs empty. Log in
   at `/settings` once, paste the credentials, save. They are stored in
   `/app/data/config.json` (the `data:` volume) with the `spotify_client_secret`
   **encrypted at rest** with `ADMIN_DATA_KEY`. Redeploys keep the file, so you
   never re-enter the credentials.

The in-app Settings screen is gated behind admin auth — see below.

## Securing your admin panel

### One-shot bootstrap

On first deploy, set:

- `ADMIN_PASSWORD` — seed for the initial `admin` user (≥ 12 chars, mix 3
  classes, **not on the bundled blocklist**). Used **once**; ignored on
  subsequent boots once the DB has a user.
- `ADMIN_SESSION_SECRET` — 32+ char random string. Signs the session cookie.
- `ADMIN_DATA_KEY` — Fernet key for at-rest encryption. Generate with:

  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

- `ADMIN_META_PEPPER` — random string, peppers IP/UA hashes in the audit log.

### Production checklist (REQUIRED)

```env
ADMIN_PASSWORD=<bootstrap only — remove after first login>
ADMIN_SESSION_SECRET=<32+ bytes random>
ADMIN_DATA_KEY=<Fernet key>
ADMIN_META_PEPPER=<random>
ADMIN_COOKIE_SECURE=1
SECURITY_HEADERS_STRICT=1
FORCE_HTTPS=1
```

Recommended for public deploys:

```env
ADMIN_STEALTH=1           # /api/admin/* → 404 when unauthenticated
ADMIN_FOOTER_LINK=false   # hide "Admin" link from the footer
ADMIN_BLOCK_GENERIC_UA=1  # reject curl/python-requests on /api/admin/*
```

Verify posture before exposing the deploy:

```bash
docker exec -it <container> python tools/check-admin-hardening.py --prod
```

Exits non-zero if any FAIL or WARN is found.

### Persistent files (back these up encrypted, **never** alongside `ADMIN_DATA_KEY`)

| Path                      | Purpose                                |
| ------------------------- | -------------------------------------- |
| `/app/data/admin.sqlite3` | Admin users, sessions, audit log       |
| `/app/data/config.json`   | Spotify credentials (secret encrypted) |
| `/app/data/queue.json`    | Download queue state                   |
| `/app/data/.session_secret` | Auto-gen session secret (if env unset) |
| `/app/data/.data_key`     | Auto-gen at-rest key (if env unset)    |

Backups that include `data/` but *not* `ADMIN_DATA_KEY` are useless to an
attacker — that's the design. Store the key out-of-band (Coolify secrets,
Bitwarden, etc).

## Runbook

### Lost / forgotten admin password

```bash
docker exec -it <container> python -m gui.backend.admin_cli reset-password admin
```

Prompts for a new password on stdin. All existing sessions are revoked.

### Locked-out user (too many failed attempts)

```bash
docker exec -it <container> python -m gui.backend.admin_cli unlock admin
```

### Rotate session secret (suspect a leak)

```bash
docker exec -it <container> python -m gui.backend.admin_cli rotate-secret
```

Invalidates **all** existing sessions. Users must log in again.

### Revoke all sessions for a user

```bash
docker exec -it <container> python -m gui.backend.admin_cli revoke-sessions admin
```

### Inspect the audit log

```bash
# JSON-structured events are also tailed in `docker compose logs` (look for
# `"audit": true`). For DB-backed query:
curl -b cookies.txt https://your.host/api/admin/audit?limit=200
```

### Suspected compromise

1. `rotate-secret` → kills sessions.
2. `reset-password admin` → kills attacker's credential.
3. Rotate `ADMIN_DATA_KEY` env: stop container, generate new key, re-encrypt
   `config.json` (re-save via UI), restart.
4. Pull `data/admin.sqlite3` and grep `admin_audit` for the attacker's IP hash.

## YouTube cookies (bot-detection bypass)

Datacenter IPs frequently hit YouTube's "Sign in to confirm you're not a bot"
wall. PO Token (already auto-fetched via `nodejs-wheel-binaries`) handles most
cases; for very burnt IPs, layer admin-uploaded cookies on top.

1. In a browser, log into `youtube.com` with a **dedicated throwaway** Google
   account (never your personal one — YouTube can sanction the account).
2. Install `Get cookies.txt LOCALLY` (Chrome/Firefox extension).
3. Export cookies on a YouTube page → `cookies.txt` (Netscape format).
4. Log into the app at `/settings`, expand "YouTube cookies", paste the full
   file contents, check "Validate on upload", click Upload.

The blob is stored encrypted at rest (`data/youtube_cookies.enc`, Fernet with
`ADMIN_DATA_KEY`) and never re-emitted. If YouTube starts rejecting them again,
the `Status` badge flips to `invalid:<reason>` — re-export from the same
account and re-upload.

To rotate or remove:

```bash
# UI
/settings → YouTube cookies → Delete stored cookies

# CLI inside container
rm /app/data/youtube_cookies.enc /app/data/youtube_cookies.meta.json
```

This feature is **complementary** to PO Token, not a replacement. With both
active, datacenter IPs survive a lot longer before getting flagged.

## Notes

- `ffmpeg` is installed in the runtime image — required for mp3/m4a/opus transcode.
- Downloaded files land in `/app/downloads` and are auto-cleaned after serving.
- `pywebview` and `google-api-python-client` are excluded from the container
  (`requirements-docker.txt`) — desktop/unused deps.
