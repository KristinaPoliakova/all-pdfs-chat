# Observability (Prometheus + Grafana) — Design Spec

- **Date:** 2026-06-03
- **Status:** Approved (design) — pending implementation plan
- **Scope:** Add metrics-based observability to the production Docker Compose stack: a Prometheus + Grafana monitoring stack scraping **FastAPI API (RED) metrics** and **host metrics** (node_exporter). Builds on the CD pipeline design (`2026-05-31-cd-pipeline-design.md`), which deferred "centralized log/metrics shipping" — this picks up the metrics half of that thread.

## 1. Context & current state

- **Stack (`docker-compose.prod.yml`):** FastAPI backend image runs both the **API** (`uvicorn app.main:app`) and the **worker** (`python -m app.worker`); plus Next.js `frontend`, `postgres`, `nginx` + `certbot`. Single DigitalOcean droplet.
- **Network:** internal `appnet`. Only `nginx` publishes ports, currently bound to `127.0.0.1:80/443` (private testing via SSH tunnel). All other services are reachable only inside `appnet` by service name.
- **Observability today:** none. Stdlib `logging` only, plus `GET /health` (liveness) and `GET /ready` (readiness). No metrics dependencies in `backend/pyproject.toml`.
- **Deploy:** GitHub Actions over SSH → `deploy/deploy.sh` (pull → backup → `alembic upgrade head` → `up -d` → recreate nginx → health gate). App images come from GHCR via the tag-triggered `release.yml`.

## 2. Decisions

| Decision | Choice |
|----------|--------|
| Layers observed | **App (FastAPI API RED metrics)** + **Host (node_exporter)** |
| Worker / Postgres / nginx / container exporters | **Out of scope** (deferred) |
| Grafana exposure | **Loopback only** — published `127.0.0.1:3001:3000`, accessed via SSH tunnel (matches current private-testing posture) |
| Alerting | **Dashboards-only** for v1 — no Alertmanager / notifications |
| Stack placement | **Separate `docker-compose.monitoring.yml`**, layered onto the prod (or dev) compose via `-f` flags; joins the same `appnet`. Independently start/stoppable. |
| App instrumentation | **`prometheus-fastapi-instrumentator`** exposing `GET /metrics` |
| `/metrics` exposure | **Internal only** — scraped by Prometheus over `appnet` (`api:8000/metrics`); never routed by nginx; no auth |
| Prometheus retention | **15 days**, named volume `promdata` |
| Grafana provisioning | **As code** — datasource + dashboards committed to the repo |
| Dashboards | **Node Exporter Full** (host) + a **FastAPI/instrumentator** request dashboard, shipped as JSON |
| Grafana admin password | From `/etc/all-pdfs-chat/monitoring.env` (mode 600); `monitoring.env.example` committed |

### Rationale notes
- **Instrumentation library:** `prometheus-fastapi-instrumentator` is the de facto FastAPI standard and gives request count/latency/in-progress out of the box. *Alternative considered:* hand-rolled `prometheus_client` middleware — more code, no benefit at this scope.
- **Separate compose file:** keeps the core prod file lean and lets monitoring be enabled/updated on its own cadence. The monitoring images are pinned and change rarely, decoupled from app releases.
- **Loopback Grafana:** nothing new is exposed publicly; consistent with the rest of the stack today.

## 3. Goals & non-goals

### Goals
- Per-request visibility into the API: rate, error rate, latency (RED).
- Host visibility: CPU, memory, **disk** (uploads + backups growth matters), network.
- Reproducible, committed Grafana config (datasource + dashboards) — no manual setup drift.
- A monitoring stack that survives app redeploys and is independently start/stoppable.
- Documented provisioning + SSH-tunnel access in `docs/deployment.md`.

### Non-goals (deferred)
- Alertmanager and notification channels.
- Worker / Postgres / nginx / container (cAdvisor) exporters.
- Log aggregation (e.g. Loki).
- Public Grafana exposure (nginx subpath/subdomain + login).
- Off-box / long-term metric storage.

## 4. Architecture

### 4.1 Topology
```
appnet (internal; only Grafana publishes a port, on loopback):

  prometheus ──scrape──> api:8000/metrics       (FastAPI RED metrics)
  prometheus ──scrape──> node-exporter:9100     (host CPU/mem/disk/net)
  prometheus ──scrape──> prometheus:9090        (self)
  grafana    ──query───> prometheus:9090
  grafana    ──published──> 127.0.0.1:3001       (SSH tunnel only)
```

### 4.2 App instrumentation (backend image)
- Add `prometheus-fastapi-instrumentator` to `backend/pyproject.toml`.
- In `app/main.py` `create_app()`, instrument the app and expose `GET /metrics`.
- **Exclude** `/health`, `/ready`, and `/metrics` from instrumentation to reduce noise.
- `/metrics` is served on the API's port 8000 and scraped directly over `appnet`. nginx proxies only `/api/v1/` (→ api) and `/` (→ frontend), so `/metrics` is **not** publicly reachable. It exposes only aggregate metrics (no secrets), so no auth is added.
- The **worker** shares the image but is **not** instrumented — only the FastAPI HTTP app exposes `/metrics`. (Worker metrics are out of scope.)

### 4.3 Monitoring services (`docker-compose.monitoring.yml`)
| Service | Image (pinned tag) | Notes |
|---------|--------------------|-------|
| `prometheus` | `prom/prometheus:<pinned>` | config mounted from `deploy/monitoring/prometheus/prometheus.yml`; volume `promdata`; `--storage.tsdb.retention.time=15d`; internal only |
| `node-exporter` | `prom/node-exporter:<pinned>` | host mounts `/proc`, `/sys`, `/` (read-only); internal only |
| `grafana` | `grafana/grafana:<pinned>` | publishes `127.0.0.1:3001:3000`; volume `grafanadata`; provisioning mounted from `deploy/monitoring/grafana/provisioning/`; admin password from `monitoring.env` |

- All services attach to the existing `appnet`. In the monitoring compose file, `appnet` is declared so that, when layered onto the prod (or dev) compose, Compose merges them into one network.
- Image tags are pinned (not `latest`) for reproducible deploys.

### 4.4 Prometheus config (`deploy/monitoring/prometheus/prometheus.yml`)
Scrape jobs:
- `prometheus` → `localhost:9090`
- `api` → `api:8000` (`/metrics`)
- `node` → `node-exporter:9100`

Default scrape interval 15s. Prometheus resolves `api` by DNS on each scrape, so it transparently follows the API container's IP across redeploys.

### 4.5 Grafana provisioning (committed to repo)
- `deploy/monitoring/grafana/provisioning/datasources/prometheus.yml` — Prometheus datasource at `http://prometheus:9090`, set as default.
- `deploy/monitoring/grafana/provisioning/dashboards/dashboards.yml` — a file provider pointing at the dashboard JSON directory.
- Dashboard JSON: **Node Exporter Full** (host) and a **FastAPI request** dashboard (rate/error/latency from instrumentator metrics).

## 5. Lifecycle & deploy integration

- **App side:** the `/metrics` change is part of the backend image, shipped through the **normal CI/release** (`release.yml`) — **no change to `release.yml` or `deploy.sh` required**.
- **Monitoring side:** its own lifecycle, brought up during provisioning:
  ```
  docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml up -d
  ```
  It survives app redeploys (Prometheus re-resolves `api` DNS per scrape — immune to the IP-churn that forces an nginx recreate in `deploy.sh`).
- **Local verification:** the same file layers onto dev —
  ```
  docker compose -f docker-compose.dev.yml -f docker-compose.monitoring.yml up -d
  ```
  — to validate dashboards/provisioning before prod.

## 6. Secrets & configuration
- **On the VM:** `/etc/all-pdfs-chat/monitoring.env` (mode 600) holds `GF_SECURITY_ADMIN_PASSWORD` (and optionally `GF_SECURITY_ADMIN_USER`), referenced by the Grafana service via `env_file`. Never committed.
- **Committed template:** `monitoring.env.example`.
- No new GitHub secrets are required (monitoring is not driven by Actions).

## 7. Testing & verification

### Automated (TDD)
- A backend test asserting `GET /metrics` returns 200 and exposes instrumentator metrics (e.g. `http_request_duration_seconds`), using the existing httpx async test client. Written before the instrumentation wiring.

### Manual
- `docker compose ... up -d` brings up `prometheus`, `node-exporter`, `grafana` healthy.
- Prometheus **Targets** page shows `api` and `node` UP.
- SSH-tunnel to `127.0.0.1:3001`; both dashboards populate with live data (generate API traffic to populate the FastAPI dashboard).
- Confirm `/metrics` is **not** reachable via the public nginx route (only over `appnet`).
- Confirm `monitoring.env` is mode 600 and no secrets are committed.

## 8. File inventory (created / modified in implementation)

**Created**
- `docker-compose.monitoring.yml`
- `deploy/monitoring/prometheus/prometheus.yml`
- `deploy/monitoring/grafana/provisioning/datasources/prometheus.yml`
- `deploy/monitoring/grafana/provisioning/dashboards/dashboards.yml`
- `deploy/monitoring/grafana/dashboards/node-exporter-full.json`
- `deploy/monitoring/grafana/dashboards/fastapi.json`
- `monitoring.env.example`

**Modified**
- `backend/pyproject.toml` (add `prometheus-fastapi-instrumentator`)
- `backend/app/main.py` (wire instrumentator + expose `/metrics`)
- backend tests (add `/metrics` test)
- `docs/deployment.md` (monitoring section: provisioning, SSH-tunnel access, operations, retention)

## 9. Risks & mitigations
| Risk | Mitigation |
|------|-----------|
| Monitoring stack consumes droplet resources (RAM/disk) | 15-day retention; pinned, lightweight images; single-VM lean config; disk visibility via node_exporter itself |
| `/metrics` accidentally exposed publicly | Internal-only scrape over `appnet`; nginx never routes `/metrics`; documented and verified |
| Grafana left with default credentials | Admin password from `monitoring.env` (mode 600); template committed, real value never |
| Prometheus disk growth unbounded | Retention cap (15d) + named volume; node_exporter alerts (future) |
| Monitoring images drift / break on pull | Pinned image tags (not `latest`) |

## 10. Deferred (future phases)
Alertmanager + notifications (API down, high error rate, low disk), worker/Postgres/nginx/container exporters, log aggregation (Loki), public Grafana exposure with auth, and off-box/long-term metric storage.
