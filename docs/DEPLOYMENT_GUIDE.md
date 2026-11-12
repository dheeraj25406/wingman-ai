# Wingman AI — Public Production Deployment Guide

This guide provides end-to-end instructions for deploying **Wingman AI** to public staging and production environments.

---

## 1. System Architecture Overview

```mermaid
graph TD
    Client["Client Browser / SRE Workstation"] -->|HTTPS :443| LB["Cloud Reverse Proxy / Ingress Nginx"]
    LB -->|HTTP :80| Frontend["Frontend Container (Nginx :80)"]
    Frontend -->|Static Assets| Client
    Frontend -->|Proxy /api/| Backend["Backend Container (Uvicorn / FastAPI :8000)"]
    
    Backend -->|Async SQLAlchemy / asyncpg| DB[(PostgreSQL 16 :5432)]
    Backend -->|HTTPS API Call| Gemini["Google Gemini 3.5 Flash-Lite API"]
    Backend -->|In-Memory Pipeline| Mesh["Microservice Telemetry Mesh & Fault Engine"]
    
    subgraph Observability [Optional Observability Profile]
        Backend -.->|Metrics| Prometheus["Prometheus (:9090)"]
        Backend -.->|Logs| Loki["Grafana Loki (:3100)"]
        Backend -.->|Traces| Tempo["Grafana Tempo (:3200)"]
    end
```

---

## 2. Infrastructure Requirements

### Minimum Recommended Specs (Single Node / VM)
- **CPU:** 2 vCPUs (x86_64 or ARM64)
- **RAM:** 4 GB minimum (8 GB recommended for concurrent fault simulation and ML evaluation)
- **Disk:** 20 GB SSD
- **Operating System:** Linux (Ubuntu 22.04 LTS / Debian 12) or macOS / Container Host
- **Runtimes:** Docker Engine 24+ and Docker Compose v2+

---

## 3. Environment Variables & Secret Configuration

Create your production configuration by copying `.env.example`:

```bash
cp .env.example .env
chmod 600 .env
```

### Essential Production Variables

| Variable | Description | Production Recommendation |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Runtime mode | Set to `production` |
| `PORT` | Backend listening port | `8000` |
| `HOST` | Backend listening host | `0.0.0.0` |
| `CORS_ORIGINS` | Allowed origins | `https://wingman.yourdomain.com` (strict origin, no wildcards) |
| `ADMIN_API_KEY` | Admin token for mutations | Strong random string (e.g. `openssl rand -hex 32`) |
| `RATE_LIMIT_ENABLED` | IP-based request throttling | `true` |
| `GEMINI_API_KEY` | Google Gemini API Key | Required for LLM investigation (`AIza...`) |
| `GEMINI_MODEL` | Investigation Model ID | `gemini-3.5-flash-lite` |
| `DATABASE_URL` | Async PostgreSQL URI | `postgresql+asyncpg://wingman:pass@postgres:5432/wingman` |
| `POSTGRES_USER` | Database user | `wingman` |
| `POSTGRES_PASSWORD`| Database password | Generated strong password |
| `POSTGRES_DB` | Database schema name | `wingman` |

---

## 4. Production Deployment with Docker Compose

### Step 1: Clone Repository & Configure Environment
```bash
git clone <repository_url> wingman-ai
cd wingman-ai
cp .env.example .env
nano .env  # Configure GEMINI_API_KEY, ADMIN_API_KEY, and POSTGRES_PASSWORD
```

### Step 2: Build and Launch Containers
```bash
docker compose up -d --build
```

### Step 3: Verify Container Health
```bash
docker compose ps
```
Expected output:
```text
NAME                IMAGE                  STATUS                   PORTS
wingman-postgres    postgres:16-alpine     Up (healthy)             0.0.0.0:5432->5432/tcp
wingman-backend     wingman-backend        Up (healthy)             0.0.0.0:8000->8000/tcp
wingman-frontend    wingman-frontend       Up (healthy)             0.0.0.0:3000->80/tcp
```

### Step 4: Run Database Migrations
Database schemas are automatically verified on startup via `lifespan`. To run or verify migrations explicitly with Alembic:
```bash
docker compose exec backend alembic upgrade head
```

---

## 5. Standalone / Bare-Metal Deployment

### 5.1 Backend Service (FastAPI)
```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Apply database migrations
PYTHONPATH=. alembic upgrade head

# 4. Run production server with Uvicorn
uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --log-level info
```

### 5.2 Frontend Service (Vite Static Build & Nginx)
```bash
# 1. Build frontend bundle
cd frontend
npm ci
npm run build

# 2. Copy compiled assets to Nginx html root
sudo cp -r dist/* /var/www/wingman/html/
```

Nginx host block sample (`/etc/nginx/sites-available/wingman.conf`):
```nginx
server {
    listen 80;
    server_name wingman.yourdomain.com;

    location / {
        root /var/www/wingman/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 6. Health & Readiness Probes

Wingman AI provides dedicated Kubernetes / Docker health check endpoints:

1. **Liveness Probe:**
   - **URL:** `GET /api/health/live` (or `GET /api/health`)
   - **Success:** HTTP 200 OK
   - **Purpose:** Verifies FastAPI runtime responsiveness.

2. **Readiness Probe:**
   - **URL:** `GET /api/health/ready`
   - **Success:** HTTP 200 OK (returns `{"status":"ready","database":"connected","models_loaded":true}`)
   - **Failure:** HTTP 503 Service Unavailable (when database connection fails)
   - **Purpose:** Controls traffic routing in Kubernetes Ingress / AWS ALB.

---

## 7. Security Best Practices

1. **CORS Restrictions:**
   Never leave `CORS_ORIGINS=*` in production. Explicitly set your frontend FQDN.
2. **Administrative Mutation Authorization:**
   Set `ADMIN_API_KEY` in `.env`. When configured, operators must supply `X-Wingman-Auth: <key>` or `Authorization: Bearer <key>` when approving remediations, triggering fault injections, or modifying traffic generator rates.
3. **API Key Isolation:**
   The `GEMINI_API_KEY` is strictly consumed server-side in Python. The `/api/settings/integrations` endpoint only exposes a masked snippet (`AIza...1234`).
4. **Rate Limiting:**
   Built-in token bucket limits client IPs to 120 requests/minute for queries and 20 requests/minute for mutating actions.
5. **Database Secrets:**
   PostgreSQL credentials are parameterized through environment variables; no default passwords should be exposed to public networks.

---

## 8. Troubleshooting & Diagnostics

### Symptom: Backend Container Health Check Failing
- **Check logs:** `docker compose logs backend`
- **Verify PostgreSQL:** `docker compose exec postgres pg_isready -U wingman`
- **Verify Database Schema:** `docker compose exec backend alembic current`

### Symptom: Gemini Investigations Falling Back to Deterministic Mode
- **Check key configuration:** In the Settings UI, verify Gemini API status.
- **Check network outbound:** Ensure the host has outbound HTTPS access to `generativelanguage.googleapis.com:443`.
- **Exceeded Quotas:** If Gemini API responds with HTTP 429/503, the investigation state machine automatically applies exponential backoff (up to 3 retries) and then transitions gracefully to deterministic evidence-grounded hypotheses.
