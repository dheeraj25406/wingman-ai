# Wingman AI — Security Architecture & Policy

**Security Classification:** Production-Hardened Reference Architecture  
**Version:** 1.0.0  

---

## 1. Authentication & Authorization Controls

### 1.1 Administrative Key Verification
- **Constant-Time Comparison:** Administrative credentials (`ADMIN_API_KEY`) are compared using `secrets.compare_digest` to prevent timing attacks.
- **Fail-Closed Production Policy:** When `ENVIRONMENT=production` and `PUBLIC_DEMO_MODE=false`, mutating API endpoints fail closed (HTTP 401/500) if `ADMIN_API_KEY` is missing or invalid.
- **Accepted Authentication Schemes:**
  - `Authorization: Bearer <ADMIN_API_KEY>`
  - `X-Wingman-Auth: <ADMIN_API_KEY>`

### 1.2 Protected Endpoint Inventory
The following endpoints require administrative authentication in production mode:
- `POST /api/faults/inject` (Simulated fault injection)
- `POST /api/faults/{id}/stop` (Fault cancellation)
- `POST /api/faults/stop-all` (Global fault cancellation)
- `POST /api/incidents/{id}/investigate` (Autonomous LLM investigation trigger)
- `POST /api/incidents/{id}/approve` (Operator remediation approval)
- `POST /api/incidents/{id}/reject` (Operator remediation rejection)
- `DELETE /api/incidents/{id}` (Incident deletion)
- `POST /api/settings/api-key` (Gemini API key runtime configuration — requires admin authorization even in demo mode)

---

## 2. Secrets Management & API Key Protection

1. **Frontend Isolation:** The Google Gemini API key (`GEMINI_API_KEY`) and database credentials are strictly server-side environment variables. They are never compiled into the Vite frontend bundle, never rendered in HTML, and never exposed in public API responses.
2. **Git Hygiene:** Local configuration files (`.env`, `.env.local`), database files (`*.db`, `*.sqlite3`), and logs are strictly ignored via [`.gitignore`](file:///Users/dheerajalamuri/Documents/Wingman%20AI/.gitignore).
3. **Template Sanitization:** [`.env.example`](file:///Users/dheerajalamuri/Documents/Wingman%20AI/.env.example) contains placeholder tokens only with zero hardcoded credentials.

---

## 3. Network Architecture & Ingress Security

### 3.1 Production Network Segmentation (`docker-compose.prod.yml`)
- **Database Isolation:** PostgreSQL operates strictly on the internal Docker bridge network (`expose: 5432`). Port 5432 is never mapped to the host interface in production.
- **Backend Ingress:** FastAPI runs internally on port 8000 and is not exposed directly to the public internet. All incoming client traffic is routed through the Nginx reverse proxy.
- **Reverse Proxy Ingress:** The production Nginx container provides the single point of entry on port 80 (or 443 with TLS termination).

### 3.2 Enterprise Security Headers
Every HTTP response processed by `SecurityMiddleware` includes defensive security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (enforced in production)

### 3.3 Rate Limiting & Proxy IP Handling
- **Sliding-Window Limiter:** Tracks requests per client IP with separate buckets:
  - General Endpoints: 120 requests/minute.
  - Sensitive Mutating Endpoints: 20 requests/minute.
- **Trusted Reverse Proxy Headers:** Extracts client IP from `X-Real-IP` set by the Nginx reverse proxy, falling back to `X-Forwarded-For` or connection host.

---

## 4. Remediation Safety Constraints

1. **Human Approval Gate:** Automated remediation actions require explicit operator approval via the UI or API before execution.
2. **Strict Action Catalog:** Only pre-approved remediation types are executable:
   - `RESTART_SERVICE`
   - `RESET_CONNECTION_POOL`
   - `ROLLBACK_DEPLOYMENT`
   - `THROTTLE_TRAFFIC`
   - `DRAIN_QUEUE`
   Arbitrary shell commands, raw SQL scripts, or container injections are architecturally impossible.
3. **Duplicate Decision Prevention:** Already executed, mitigated, or resolved incidents reject duplicate approval or rejection calls with HTTP 400 Bad Request.

---

## 5. Dependency Vulnerability Audits

### 5.1 Python Backend (`pip-audit`)
- Audit status: **Zero known vulnerabilities found** across all installed Python packages.

### 5.2 Node.js Frontend (`npm audit`)
- Audit status: **Zero high or critical vulnerabilities**.
- Moderate Advisories: 2 moderate advisories in `react-router` / `react-router-dom` (CVE-2025-68470 open redirect via backslash, and constructor injection in SSR hydration). Because Wingman AI is deployed as a purely client-side Single Page Application (SPA) without SSR hydration, these vulnerabilities have no exploitable attack surface.

---

## 6. Reporting a Vulnerability

If you discover a security vulnerability within Wingman AI, please report it privately by opening a confidential security advisory on GitHub or emailing the maintainers. Please do not publish security issues in public issue trackers until a patched release is available.
