# CD Pipeline — Design Spec

- **Date:** 2026-05-31
- **Status:** Approved (design) — pending implementation plan
- **Scope:** Continuous Deployment of the containerized app to a single DigitalOcean droplet via Docker Compose, triggered by version tags. Builds on the CI work (`2026-05-31-ci-pipeline-design.md`) and the Dockerfiles it added.

## 1. Context & current state

The app is already **container-ready** from the CI phase:

- `backend/Dockerfile` — one image runs the **API** (`uvicorn app.main:app`) and the **worker** (`python -m app.worker`).
- `frontend/Dockerfile` — Next.js **standalone** image.
- `.github/workflows/ci.yml` — builds both images on push (`push: false`, validation only).
- `docker-compose.yml` — **dev only** (Postgres service for local development).

No deployment is automated yet. Pre-existing docs describe a **legacy systemd-on-a-VM** plan (`backend/.env.production.example`, `frontend/.env.production.example`, `scripts/README.md`); those are now superseded by this Compose-based design and will be reconciled during implementation.

Relevant app facts that shape this design:

- **Two long-running processes:** API and worker (separate containers, same image).
- **Storage backends:** `local` (disk) or `azure` (Blob). Production will use **local disk** (`STORAGE_BACKEND=local`, `LOCAL_STORAGE_PATH`).
- **Migrations:** Alembic, version-controlled. In **prod**, startup **fails on a stale schema** (`init_database()` checks Alembic head) — so migrations MUST run before the API/worker (re)start.
- **Health endpoints:** `GET /health` (liveness), `GET /ready` (readiness — app up + `SELECT 1`).
- **Intended prod routing (per `backend.md`):** one domain, nginx proxies `/api/v1` to the backend, `CORS_ALLOWED_ORIGINS` empty.
- **Prod env templates** already target `/etc/all-pdfs-chat/*.env` and `LOCAL_STORAGE_PATH=/var/lib/all-pdfs-chat/uploads`.

## 2. Decisions

| Decision | Choice |
|----------|--------|
| Host | Single DigitalOcean droplet |
| Orchestration | Docker Compose (`docker-compose.prod.yml`) |
| PDF storage | Local disk via a Docker **named volume** (`uploads`) shared by api + worker |
| PostgreSQL | **In Compose** on the VM (`postgres:16.6-alpine` + named volume `pgdata`); backups owned by us |
| Image registry | **GHCR** (`ghcr.io/kristinapoliakova/all-pdfs-chat-{backend,frontend}`) |
| Deploy trigger | **Git tag** `vX.Y.Z` (SemVer) / GitHub Release |
| Deploy mechanism | **GitHub Actions over SSH** runs `deploy.sh` on the droplet |
| Reverse proxy / TLS | **nginx + Certbot** (Let's Encrypt, webroot method) |
| Infra provisioning | **Manual runbook** (documented), not Terraform/Ansible |
| TLS renewal & backups | Host **cron** |
| GHCR auth on VM | One-time `docker login` with a `read:packages` PAT |
| Downtime model | Brief container-recreate window (NOT zero-downtime) — acceptable for a solo single-VM app |

### Deploy-mechanism rationale
A stateful app with migrations needs a **correct ordered sequence** (pull → back up DB → migrate → restart → health-check). Actions-over-SSH orchestrates that with logs and a health gate. Pull-based auto-updaters (watchtower) are rejected — no control over migration ordering or backups. A manual deploy script is **also** shipped (`deploy.sh`); Actions simply invokes it, so it can be run by hand if Actions is unavailable.

## 3. Goals & non-goals

### Goals
- One-command/tag-driven, repeatable, logged production deploys.
- Correct migration ordering and a mandatory pre-deploy DB backup.
- TLS-terminated single domain serving frontend + API.
- A documented greenfield provisioning runbook and a rollback procedure.
- Reconcile the stale systemd docs.

### Non-goals (deferred / out of scope)
- Zero-downtime / blue-green / rolling deploys.
- Multi-VM, autoscaling, or orchestrators (k8s/Nomad).
- Managed Postgres or Azure Blob storage (explicitly chose in-VM Postgres + local disk).
- IaC (Terraform/Ansible) — manual runbook for one VM (easy follow-up later).
- Staging environment (single prod environment for now).

## 4. Architecture

### 4.1 Topology
```
Internet ──80/443──> nginx (TLS termination, reverse proxy)
                       ├── /api/v1/*  ─> api:8000        (FastAPI)
                       └── /*         ─> frontend:3000   (Next.js standalone)

  docker network "appnet" (internal; only nginx publishes ports):
    api      ─> postgres:5432         worker  ─> postgres:5432
    api & worker  ─> volume "uploads" (/var/lib/all-pdfs-chat/uploads)
    postgres ─> volume "pgdata"
    nginx & certbot ─> volumes "certs" + "certbot-webroot"
```

### 4.2 Services (`docker-compose.prod.yml`)
| Service | Image | Notes |
|---------|-------|-------|
| `postgres` | `postgres:16.6-alpine` | volume `pgdata`; healthcheck `pg_isready`; **internal only** |
| `api` | `ghcr.io/.../backend:${IMAGE_TAG}` | `env_file: /etc/all-pdfs-chat/backend.env`; mounts `uploads`; `depends_on: postgres (healthy)`; internal only |
| `worker` | `ghcr.io/.../backend:${IMAGE_TAG}` | command `python -m app.worker`; same env_file + `uploads`; `depends_on: postgres (healthy)` |
| `frontend` | `ghcr.io/.../frontend:${IMAGE_TAG}` | `env BACKEND_URL=http://api:8000`, `HOSTNAME=0.0.0.0`, `env_file: frontend.env`; internal only |
| `nginx` | `nginx:1.27-alpine` | publishes 80/443; config from `deploy/nginx/`; mounts `certs` + webroot |
| `certbot` | `certbot/certbot` | issues/renews certs via webroot; run on demand / by cron |

- `${IMAGE_TAG}` is supplied at deploy time (written into `/etc/all-pdfs-chat/deploy.env` or passed inline). Defaults to `latest` for manual runs.
- nginx routes `/api/v1` **directly** to `api` (the Next rewrite remains a harmless fallback). `CORS_ALLOWED_ORIGINS` stays empty (same origin).

### 4.3 Routing & TLS
- Single domain (e.g. `app.example.com`). nginx server block: TLS 443, HTTP→HTTPS redirect on 80, `location /api/v1/ → http://api:8000`, `location / → http://frontend:3000`, plus an ACME `location /.well-known/acme-challenge/` served from the webroot volume.
- **Bootstrap order** (solves the cert chicken-and-egg): (1) bring up nginx with an HTTP-only config exposing the ACME path; (2) run certbot once to issue; (3) swap in the HTTPS config and reload nginx.
- **Renewal:** host cron, twice daily: `docker compose run --rm certbot renew && docker compose exec nginx nginx -s reload`.

## 5. Release flow (trigger: tag `vX.Y.Z`)

`.github/workflows/release.yml`:

```
on: push: tags: ['v*.*.*']   (+ workflow_dispatch with an image-tag input)

job build-and-push (GitHub-hosted):
  - permissions: contents: read, packages: write
  - docker/login-action -> ghcr.io (GITHUB_TOKEN)
  - build + push backend image  -> :${tag} and :latest
  - build + push frontend image -> :${tag} and :latest

job deploy (needs build-and-push):
  - appleboy/ssh-action (or raw ssh) using secrets SSH_HOST/SSH_USER/SSH_PRIVATE_KEY[/SSH_PORT]
  - run on the droplet:  IMAGE_TAG=${tag}  bash /opt/all-pdfs-chat/deploy.sh
```

`deploy/deploy.sh` (runs on the VM, idempotent):
```
1. cd /opt/all-pdfs-chat
2. write IMAGE_TAG into deploy.env
3. docker compose -f docker-compose.prod.yml pull
4. backup.sh            # pg_dump -Fc (pre-deploy safety net)
5. docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
6. docker compose -f docker-compose.prod.yml up -d
7. health gate: poll http://localhost/ (via nginx) and api /ready; nonzero exit on failure
8. docker image prune -f   # reclaim space
```

- **Migration ordering** is guaranteed: migrate (step 5) before app recreate (step 6). Matches the prod "fail on stale schema" rule.
- **Rollback:** re-run with a previous `IMAGE_TAG` (`workflow_dispatch` or run `deploy.sh` by hand). DB rollback via `alembic downgrade` + restoring the pre-deploy `pg_dump` (runbook).

## 6. Backups (`deploy/backup.sh` + cron)
- **Pre-deploy:** invoked by `deploy.sh` (mandatory before migrate).
- **Scheduled:** nightly host cron — `pg_dump -Fc` of the DB + `tar` of the `uploads` volume into `/var/backups/all-pdfs-chat/`, timestamped, with simple retention (e.g. keep 14 days).
- Restore procedure documented in the runbook (`pg_restore` + untar into the volume).

## 7. Secrets & configuration
- **On the VM:** `/etc/all-pdfs-chat/backend.env` and `/etc/all-pdfs-chat/frontend.env` (mode 600), referenced by Compose `env_file`. Created from the `.env.production.example` templates. Never committed.
- **GitHub repo secrets:** `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, optional `SSH_PORT`. (Image push uses the built-in `GITHUB_TOKEN`.)
- **GHCR pull on VM:** one-time `docker login ghcr.io` with a `read:packages` PAT (documented).
- Production `DATABASE_URL` points at the in-compose `postgres` service host (`postgres`), e.g. `postgresql+asyncpg://all_pdfs_chat:<pw>@postgres:5432/all_pdfs_chat`.

## 8. Greenfield provisioning runbook (one-time, manual)
Documented steps (no IaC): create droplet → install Docker Engine + Compose plugin → create non-root `deploy` user + add CI SSH public key → UFW allow 22/80/443 → point DNS A-record to the droplet → create `/opt/all-pdfs-chat/` and copy `docker-compose.prod.yml` + `deploy/` → create `/etc/all-pdfs-chat/*.env` → `docker login ghcr.io` → TLS bootstrap (HTTP nginx → certbot issue → HTTPS reload) → first `deploy.sh` (or `up -d`) → install backup + renewal cron jobs.

## 9. File inventory (created / modified in implementation)
**Created**
- `docker-compose.prod.yml`
- `deploy/nginx/app.http.conf` (bootstrap) and `deploy/nginx/app.conf` (HTTPS)
- `deploy/deploy.sh`, `deploy/backup.sh`
- `.github/workflows/release.yml`
- `docs/deployment.md` (provisioning + operations + rollback runbook)

**Modified**
- `backend/.env.production.example`, `frontend/.env.production.example` (align with Compose: service-host `DATABASE_URL`, volume paths, `BACKEND_URL`)
- `scripts/README.md` (replace the legacy systemd env-table notes with a pointer to `docs/deployment.md`)
- `backend/backend.md` (note Compose-based prod deployment)

## 10. Verification plan
- **Dry run on the droplet:** `deploy.sh` with a known tag → images pulled, backup created, `alembic upgrade head` succeeds, all containers healthy, `https://<domain>/` serves the frontend and `https://<domain>/api/v1/...` reaches the API (`/ready` returns ready).
- **TLS:** valid Let's Encrypt cert; HTTP redirects to HTTPS; `certbot renew --dry-run` passes.
- **Migration ordering:** deploy a tag containing a new migration → confirm schema upgraded before api/worker accept traffic; no stale-schema startup failure.
- **Rollback:** redeploy the previous tag → app serves the prior version; documented DB restore tested against a dump.
- **Backups:** nightly cron produces a dump + uploads archive; a restore drill succeeds on a throwaway target.
- **Secrets:** no secrets in git or images; `/etc/all-pdfs-chat/*.env` are mode 600.

## 11. Risks & mitigations
| Risk | Mitigation |
|------|-----------|
| Brief downtime on deploy | Accepted (solo, single VM); documented |
| Local-disk uploads not redundant | Nightly backup + documented restore; can migrate to Azure Blob later (already supported) |
| Single-VM Postgres = single point of failure | Backups + restore drill; managed DB is a future option |
| Cert issuance/renewal failure | `--dry-run` in verification; renewal cron + alert on failure (log) |
| Failed migration mid-deploy | Pre-deploy `pg_dump`; deploy aborts before `up -d` if `alembic upgrade` fails |
| Disk exhaustion (images/backups/uploads) | `docker image prune` in deploy; backup retention; monitor disk |

## 12. Deferred (future phases)
Zero-downtime deploys, staging environment, IaC (Ansible/Terraform), managed Postgres, Azure Blob storage, centralized log/metrics shipping, and automated off-box backup storage (e.g. DO Spaces/S3).
