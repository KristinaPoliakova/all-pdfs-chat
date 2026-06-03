# Deployment

Production runs on a single DigitalOcean droplet via Docker Compose
(`docker-compose.prod.yml`): nginx (TLS) → frontend + api, plus worker and
postgres. Images are published to GHCR and deployed by the `Release` GitHub
Actions workflow on a `vX.Y.Z` tag.

## 1. One-time droplet provisioning (greenfield)

> `sudo` steps run as an admin user on the droplet; the app itself runs as the
> unprivileged **`deploy`** user, so several resources are owned by `deploy`.
> Step 6 (`scp`) runs **from your local machine**; the rest run on the droplet.

1. **Create the droplet** (Ubuntu LTS) and a DNS **A record** pointing your domain at its IP.
2. **Install Docker Engine + Compose plugin:**
   ```bash
   curl -fsSL https://get.docker.com | sh
   docker compose version
   ```
3. **Create the `deploy` user** and add your CI SSH **public** key:
   ```bash
   sudo adduser --disabled-password --gecos "" deploy
   sudo usermod -aG docker deploy
   sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
   sudo nano /home/deploy/.ssh/authorized_keys   # paste the CI public key
   sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys && sudo chmod 600 /home/deploy/.ssh/authorized_keys
   ```
4. **Firewall:**
   ```bash
   sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw --force enable
   ```
5. **App dir + backup/log paths (owned by `deploy`):**
   ```bash
   sudo install -d -o deploy -g deploy /opt/all-pdfs-chat
   sudo install -d -o deploy -g deploy /var/backups/all-pdfs-chat
   sudo install -o deploy -g deploy -m 644 /dev/null /var/log/all-pdfs-chat-backup.log
   ```
6. **Place deploy files + env templates on the droplet (from your local machine):**
   ```bash
   scp docker-compose.prod.yml deploy@<host>:/opt/all-pdfs-chat/
   scp -r deploy deploy@<host>:/opt/all-pdfs-chat/
   scp backend/.env.production.example  deploy@<host>:/opt/all-pdfs-chat/backend.env.example
   scp frontend/.env.production.example deploy@<host>:/opt/all-pdfs-chat/frontend.env.example
   ```
7. **Secret env files** (owned by `deploy`, who runs Compose):
   ```bash
   sudo install -d -o deploy -g deploy -m 750 /etc/all-pdfs-chat
   sudo cp /opt/all-pdfs-chat/backend.env.example  /etc/all-pdfs-chat/backend.env
   sudo cp /opt/all-pdfs-chat/frontend.env.example /etc/all-pdfs-chat/frontend.env
   sudo chown deploy:deploy /etc/all-pdfs-chat/*.env
   sudo chmod 600 /etc/all-pdfs-chat/*.env
   sudo nano /etc/all-pdfs-chat/backend.env   # set a strong DB password in DATABASE_URL (host: postgres)
   ```
8. **Compose interpolation env** `/opt/all-pdfs-chat/.env` (owned by `deploy`, mode 600):
   ```bash
   sudo -u deploy tee /opt/all-pdfs-chat/.env >/dev/null <<'EOF'
   POSTGRES_PASSWORD=<same password as in backend.env DATABASE_URL>
   IMAGE_TAG=latest
   EOF
   sudo chmod 600 /opt/all-pdfs-chat/.env
   ```
   > `POSTGRES_PASSWORD` here MUST equal the password embedded in `backend.env`'s `DATABASE_URL`.
9. **Authenticate to GHCR as the `deploy` user** (images are private; `deploy` runs the pulls):
   ```bash
   sudo -u deploy bash -c 'echo <PAT> | docker login ghcr.io -u kristinapoliakova --password-stdin'
   ```
   `<PAT>` is a GitHub token with `read:packages`.

## 2. First bring-up + TLS (first time)

Run as the `deploy` user from `/opt/all-pdfs-chat`. Order matters: seed a
temporary cert so nginx can start, bring the stack up (migrations first), then
replace the temporary cert with a real one.

> **Images must already exist in GHCR.** Push your first `vX.Y.Z` tag (the
> `Release` workflow builds + pushes them and runs the deploy — see §3) or
> build/push manually. Seeding the dummy cert (step 1) **before** that first
> deploy is what prevents nginx from failing when the stack first comes up.

```bash
cd /opt/all-pdfs-chat
C="docker compose -f docker-compose.prod.yml"

# 1) temporary self-signed cert so nginx can start on 443 (uses only the public certbot image)
$C run --rm --entrypoint sh certbot -c '
  mkdir -p /etc/letsencrypt/live/app &&
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /etc/letsencrypt/live/app/privkey.pem \
    -out    /etc/letsencrypt/live/app/fullchain.pem -subj "/CN=localhost"'

# 2) bring up the stack — migrations BEFORE the app (prod startup fails on an empty/stale schema).
#    (Or push your first tag and let the Release workflow run deploy.sh instead of these three.)
$C up -d postgres
$C run --rm api alembic upgrade head
$C up -d

# 3) replace the temporary cert with a real one. Remove the self-signed material first so
#    certbot writes the canonical live/app lineage (otherwise it creates live/app-0001 and
#    nginx keeps serving the dummy cert):
$C run --rm --entrypoint sh certbot -c \
  'rm -rf /etc/letsencrypt/live/app /etc/letsencrypt/archive/app /etc/letsencrypt/renewal/app.conf'
$C run --rm certbot certonly \
  --webroot -w /var/www/certbot --cert-name app \
  -d <your-domain> --email <you@example.com> --agree-tos --no-eff-email
$C exec nginx nginx -s reload

# verify renewal works (no rate-limit hit)
$C run --rm certbot renew --dry-run
```

Verify: `https://<domain>/` serves the app, `https://<domain>/api/v1/...`
reaches the API, and `$C ps` shows services healthy.

## 3. Routine deploys (CI)

Configure GitHub repo **secrets**: `SSH_HOST`, `SSH_USER` (`deploy`),
`SSH_PRIVATE_KEY` (the private key matching the public key from §1.3), and
optionally `SSH_PORT`.

Deploy by tagging a release:
```bash
git tag v1.0.0 && git push origin v1.0.0
```
The `Release` workflow builds + pushes images to GHCR, copies
`docker-compose.prod.yml` + `deploy/` to the droplet, and runs
`deploy/deploy.sh` (pull → backup → `alembic upgrade head` → `up -d` →
recreate nginx → `/ready` health gate).

## 4. Cron jobs (as the deploy user: `crontab -e`)

```cron
# Nightly backup at 02:30
30 2 * * * cd /opt/all-pdfs-chat && APP_DIR=/opt/all-pdfs-chat bash deploy/backup.sh scheduled >> /var/log/all-pdfs-chat-backup.log 2>&1
# TLS renewal twice daily
0 3,15 * * * cd /opt/all-pdfs-chat && docker compose -f docker-compose.prod.yml run --rm certbot renew --quiet && docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## 5. Rollback

Re-deploy a previous image tag (no rebuild) via **Actions → Release → Run
workflow** with `image_tag = v<previous>`, or on the droplet:
```bash
cd /opt/all-pdfs-chat && IMAGE_TAG=v<previous> bash deploy/deploy.sh
```
To undo a migration, restore the pre-deploy dump:
```bash
cd /opt/all-pdfs-chat
C="docker compose -f docker-compose.prod.yml"
$C stop api worker frontend
$C exec -T postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -U all_pdfs_chat -d all_pdfs_chat --clean --if-exists' \
  < /var/backups/all-pdfs-chat/db-predeploy-<timestamp>.dump
$C up -d
```

## 6. Operations cheatsheet

```bash
C="docker compose -f docker-compose.prod.yml"
$C ps               # service status
$C logs -f api      # tail API logs
$C logs -f worker   # tail worker logs
$C exec api alembic current   # current DB revision
```

## Monitoring (Prometheus + Grafana)

Metrics observability is an opt-in stack layered onto the prod compose via a
second `-f` file (`docker-compose.monitoring.yml`). It scrapes the API's
`/metrics` endpoint and host metrics (node_exporter); Grafana is published
**only on `127.0.0.1:3001`** and reached via SSH tunnel. Dashboards-only — no
alerting yet.

### One-time setup (on the droplet)
1. Place the monitoring files on the droplet (from your local machine):
   ```bash
   scp docker-compose.monitoring.yml deploy@<host>:/opt/all-pdfs-chat/
   scp -r deploy/monitoring deploy@<host>:/opt/all-pdfs-chat/deploy/
   ```
2. Create the Grafana admin secret (mode 600):
   ```bash
   # /etc/all-pdfs-chat already exists from the provisioning section above.
   sudo -u deploy install -m 600 /dev/null /etc/all-pdfs-chat/monitoring.env
   sudo -u deploy nano /etc/all-pdfs-chat/monitoring.env   # set from monitoring.env.example
   ```
3. Start the stack (alongside the running app):
   ```bash
   cd /opt/all-pdfs-chat
   docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml up -d
   ```

The monitoring stack has its own lifecycle and survives app redeploys:
`deploy.sh` only operates on the app compose file, so Prometheus, Grafana, and
node-exporter are untouched during deploys (the API may be briefly unreachable
mid-deploy; Prometheus simply records failed scrapes for that window).

### Accessing Grafana (SSH tunnel)
```bash
ssh -N -L 3001:127.0.0.1:3001 deploy@<host>
# then open http://localhost:3001 in your browser
```
Dashboards: **Host — node_exporter** and **FastAPI — API Overview**.

### Notes
- `/metrics` is internal-only (scraped over `appnet`); nginx never routes it.
- Prometheus retains 15 days of data in the `promdata` volume.
- To stop monitoring without touching the app:
  `docker compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml stop prometheus node-exporter grafana`
- **Deferred:** Alertmanager/notifications, and worker/Postgres/nginx exporters.
