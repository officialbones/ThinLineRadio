# AGENTS.md

## Cursor Cloud specific instructions

ThinLine Radio is a single-product Go + Angular radio-scanner SaaS app. The Go server (`server/`) serves the API and embedded web UI; the Angular app lives in `client/`.

### Required local services

| Service | Role | Notes |
|---|---|---|
| PostgreSQL 16 | Required DB | Only supported DB (SQLite removed). Start with `sudo pg_ctlcluster 16 main start` if not already online (no systemd in Cloud VMs). |
| ThinLine Go server | API + UI | `cd server && go run . -config $(pwd)/thinline-radio.ini` (default listen `:3000`) |
| FFmpeg / ffprobe | Audio encode | Already expected on PATH for call processing |

Optional: Stripe, SMTP, transcription providers, OneSignal — configure later via Admin → Options. Not required to boot or use the admin dashboard.

### Toolchain gotchas

- **Go 1.24+** is required (`server/go.mod`). System packages may ship older Go; prefer `/usr/local/go/bin` on `PATH`.
- **Node 18** is the practical choice for Angular 15 (`client/`). Newer Node (22+) can break the Angular 15 toolchain; use `nvm use 18`.
- Client install: `npm --prefix client install --legacy-peer-deps`.
- Go/tests need a built `server/webapp` tree because of `//go:embed all:webapp`. Run `npm --prefix client run build` before `go test ./...` or `go run .` if `server/webapp` is missing.
- There is **no** root `Makefile` despite `COMPILING.md` mentioning `make`.
- Client has ESLint config but **no** `lint` / `test` npm scripts; Karma is referenced in `angular.json` but unwired. Lint manually with `npx eslint` under `client/`.

### Config

- Copy `server/thinline-radio.ini.template` → `server/thinline-radio.ini` and set `db_*` for local Postgres. Do not commit the real ini (local secrets).
- Default admin password after fresh DB is `admin` (change immediately). Admin JWT is sent as the raw `Authorization` header value (no `Bearer ` prefix).
- Failed admin logins are IP rate-limited; if `/api/admin/login` starts returning empty `401`s from localhost after bad attempts, restart the Go process to clear the in-memory limiter (or wait).

### Dev servers / ports

- Production-like (recommended for cloud agents): build the client into `server/webapp`, then run only the Go server on `:3000`. Admin UI: `http://127.0.0.1:3000/admin`.
- `npm run dev` (root) starts Go + `ng serve` concurrently, but **both default to port 3000** and `client/src/proxy.conf.js` targets `:3000`. For true dual-process hot reload, put Go on another port (e.g. `listen = 0.0.0.0:3001` in the ini) and point the proxy at that port before running `ng serve`.
- Standard scripts: root `package.json` (`dev` / `server` / `client`), client `npm start` / `npm run build`. Docker path: `./docker-deploy.sh` (interactive; prefer manual compose for automation). See `README.md`, `docker/DOCKER.md`, `docs/setup-and-administration.md`.

### Lint / test / run (quick reference)

- Go tests: `cd server && go test ./...` (after client build embeds webapp).
- Client build: `cd client && npm run build`.
- Client lint (manual): `cd client && npx eslint "src/**/*.ts"`.
- App: Go on `:3000` after Postgres is up and `thinline-radio.ini` exists.
