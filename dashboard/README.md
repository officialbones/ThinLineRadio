# ThinLine Vertical Ops Dashboard

Native **PySide6** kiosk for a **9:16** vertical monitor (default 1080×1920). Not a web app — runs on the machine in front of the display.

## What it shows

1. **County Pulse activity** — every 5 minutes pulls `GET /api/transcriptions` for systems Jay (11), Randolph (7), Blackford (56), Wells (57), Adams (58), Delaware (59), State Interop (60), AirMed (61).
2. **Address overlay** — when a street address appears in a new transcript, pops map (hybrid) + Street View images.
3. **Health** — every 5 seconds: Postgres last call / talkgroup, plus host TCP, ThinLine `/api/health/live`, and Postgres connectivity for the SDR machine.
4. **Publer** — last 3 published posts via Publer API.

## Windows setup

```powershell
cd dashboard
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env
python main.py
```

If County Pulse returns Cloudflare/403 from a datacenter IP, run the dashboard on your home/office PC (same place as your existing Python sweep script) — browser-style headers are already set.

Development (windowed 9:16):

```powershell
python main.py --windowed
```

Exit fullscreen with `Esc` or `Q`.

## `.env` keys

| Variable | Purpose |
|----------|---------|
| `PULSE_API_BASE` | County Pulse transcriptions URL |
| `PULSE_SYSTEM_IDS` | Comma-separated system refs |
| `POSTGRES_DSN` | Read-only Postgres on the radio / ThinLine host |
| `CALL_STALE_SECONDS` | Mark scanner DEGRADED if last call older than this (default 120) |
| `REMOTE_HOST` / `REMOTE_TCP_PORT` | Other PC reachability |
| `TLR_HEALTH_URL` | e.g. `http://192.168.x.x:3000/api/health/live` |
| `TLR_HEALTH_USER` / `TLR_HEALTH_PASSWORD` | Admin basic auth if required |
| `GOOGLE_MAPS_API_KEY` | Geocoding + Maps Static + Street View Static |
| `PUBLER_API_KEY` | From Publer → Settings → Access & Login → API Keys |
| `PUBLER_WORKSPACE_ID` | Workspace id header for Publer |
| `ADDRESS_DEFAULT_CITY` | Optional geocode bias (e.g. `Portland, IN`) |

Never commit `.env`. Image cache lives in `dashboard/cache/`.

## Publer notes

Docs: https://publer.com/docs  

Headers used:

```http
Authorization: Bearer-API YOUR_API_KEY
Publer-Workspace-Id: YOUR_WORKSPACE_ID
```

Poll interval defaults to 120 seconds (Publer rate limit is 100 requests / 2 minutes).

## Google Maps notes

Enable these APIs on the key:

- Geocoding API
- Maps Static API
- Street View Static API

## Layout

Designed for a portrait panel. Override size with `--width` / `--height` if your panel is 1440×2560 or similar; keep a 9:16 ratio.
