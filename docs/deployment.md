# Deployment

Production runs on a single DigitalOcean droplet via Docker Compose
(`docker-compose.prod.yml`): nginx (TLS) → frontend + api, plus worker and
postgres. Images are published to GHCR and deployed by the `Release` GitHub
Actions workflow on a `vX.Y.Z` tag.

## 1. One-time droplet provisioning (greenfield)

1. **Create the droplet** (Ubuntu LTS) and a DNS **A record** pointing your domain at its IP.
2. **Install Docker Engine + Compose plugin:**
   ```bash
   curl -fsSL https://get.docker.com | sh
   docker compose version
   ```
3. **Create a deploy user** and add your CI SSH **public** key to `~/.ssh/authorized_keys`:
   ```bash
   adduser --disabled-password --gecos "" deploy
   usermod -aG docker deploy
   install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
   nano /home/deploy/.ssh/authorized_keys   # paste the CI public key
   chown deploy:deploy /home/deploy/.ssh/authorized_keys && chmod 600 /home/deploy/.ssh/authorized_keys
   ```
4. **Firewall:**
   ```bash
   ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
   ```
5. **App directory + secret env files:**
   ```bash
   sudo install -d -o deploy -g deploy /opt/all-pdfs-chat
   sudo install -d -m 750 /etc/all-pdfs-chat
   sudo cp backend/.env.production.example  /etc/all-pdfs-chat/backend.env
   sudo cp frontend/.env.production.example /etc/all-pdfs-chat/frontend.env
   sudo chmod 600 /etc/all-pdfs-chat/*.env
   sudo nano /etc/all-pdfs-chat/backend.env    # set a strong DB password in DATABASE_URL (host: postgres)
   ```
6. **Compose interpolation env** `/opt/all-pdfs-chat/.env` (owned by deploy, mode 600):
   ```bash
   cat > /opt/all-pdfs-chat/.env <<'EOF'
   POSTGRES_PASSWORD=<same password as in backend.env DATABASE_URL>
   IMAGE_TAG=latest
   EOF
   chmod 600 /opt/all-pdfs-chat/.env
   ```
   > `POSTGRES_PASSWORD` here MUST equal the password embedded in `backend.env`'s `DATABASE_URL`.
7. **Authenticate to GHCR** (read-only PAT with `read:packages`) — required because the images are private by default:
   ```bash
   echo <PAT> | docker login ghcr.io -u kristinapoliakova --password-stdin
   ```
8. **Place the deploy files** (first time; CI keeps them in sync afterwards). From your machine:
   ```bash
   scp docker-compose.prod.yml -r deploy/ deploy@<host>:/opt/all-pdfs-chat/
   ```

## 2. TLS bootstrap + first bring-up (first time)

The nginx config references `/etc/letsencrypt/live/app/`. Seed a temporary
self-signed cert so nginx can start, run migrations before the app starts
(prod startup fails on an empty/stale schema), bring everything up, then
replace the cert with a real one.

> Images must already exist in GHCR. Either push a `vX.Y.Z` tag first (the
> `Release` workflow builds + pushes them — see §4), or build/push manually.
> `IMAGE_TAG` in `/opt/all-pdfs-chat/.env` selects which tag is pulled.

```bash
cd /opt/all-pdfs-chat
C="docker compose -f docker-compose.prod.yml"

# 1) temporary self-signed cert so nginx can start on 443
$C run --rm --entrypoint sh certbot -c '
  mkdir -p /etc/letsencrypt/live/app &&
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /etc/letsencrypt/live/app/privkey.pem \
    -out    /etc/letsencrypt/live/app/fullchain.pem -subj "/CN=localhost"'

# 2) start postgres and apply migrations BEFORE the app starts
$C up -d postgres
$C run --rm api alembic upgrade head

# 3) bring up the whole stack
$C up -d

# 4) issue the real certificate (replace domain + email)
$C run --rm certbot certonly \
  --webroot -w /var/www/certbot --cert-name app \
  -d <your-domain> --email <you@example.com> --agree-tos --no-eff-email --force-renewal

# 5) reload nginx to use the real cert
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
