# EHR Data Explorer — DevOps Deployment Guide

Short handoff for deploying the app to a web portal.

---

## What you are deploying

| Layer | Tech | Notes |
|-------|------|--------|
| **UI** | React (Vite build) | Static files in `frontend/dist/` |
| **API** | Python FastAPI + Uvicorn | Serves API + built UI |
| **Database** | Neo4j 5.x | Database name: `fhirexplorer` |

**Repo:** https://github.com/HekmaAI/ehr-data  
**Branch:** `develop`

---

## Architecture

```
Browser → HTTPS (443) → Reverse proxy → Uvicorn :8002 → Neo4j :7687 (private)
```

Production uses **one app process**: Uvicorn serves both the API and the React build.

---

## Server requirements

| Item | Minimum |
|------|---------|
| Python | 3.10+ |
| Node.js | 18+ (build step only) |
| App RAM | 2 GB |
| Neo4j RAM | 8 GB+ (scale with data) |
| Neo4j disk | 20 GB+ |

---

## Environment variables

Copy `.env.example` → `.env` (use secrets manager in prod).

**Required:**

```env
NEO4J_URI=bolt://<neo4j-host>:7687
NEO4J_USER=neo4j
NEO4J_PASS=<secret>
NEO4J_DATABASE=fhirexplorer
```

**Optional:** `LOG_LEVEL=INFO`, `MAX_SEARCH_RESULTS=25`, `MAX_PATIENT_RESULTS=50`

Do **not** commit `.env` to Git.

---

## Frontend ↔ backend integration (for DevOps)

The UI talks to the API over HTTP. **Integration is mostly automatic** — you do not mirror backend secrets in the frontend.

### How the browser calls the API

| API paths (from UI) | Backend handler |
|---------------------|-----------------|
| `GET /health` | Health + Neo4j status |
| `GET /cohort/filters` | Filter options |
| `POST /cohort/search` | Cohort search |
| `POST /search` | Concept search |
| `POST /graph/*` | Graph expand + analytics |

Frontend code: `frontend/src/api/api.js` → `fetch(\`${BASE_URL}${path}\`)`  
`BASE_URL` = `VITE_API_URL` if set, otherwise **empty** (same origin).

### Two deployment patterns

**Pattern A — Same host (recommended, no frontend env file)**

```
https://ehr.company.com/
    ├── /              → React UI (frontend/dist)
    ├── /assets/*      → JS/CSS
    ├── /health        → FastAPI
    ├── /cohort/*      → FastAPI
    ├── /search        → FastAPI
    └── /graph/*       → FastAPI
```

- **Backend `.env`:** required (Neo4j credentials)
- **Frontend `.env`:** not needed
- **Build:** `cd frontend && npm ci && npm run build`
- **Run:** `uvicorn app.main:app --port 8002` (serves UI + API)

**Pattern B — Split hosts (frontend env required at build time)**

```
https://app.company.com     → static UI (CDN/nginx)
https://api.company.com     → FastAPI only
```

Create `frontend/.env.production`:

```env
VITE_API_URL=https://api.company.com
```

Then `npm run build`. Rebuild if API URL changes.

### Development vs production

| | Dev | Production |
|---|-----|--------------|
| UI | Vite `:5174` | Built static files |
| API | Uvicorn `:8002` | Uvicorn `:8002` (or behind proxy) |
| How UI finds API | Vite proxy in `vite.config.js` | Same origin (A) or `VITE_API_URL` (B) |
| Frontend `.env` | Not required | Only for Pattern B |

### Env files summary

| File | Required? | Purpose |
|------|-----------|---------|
| `.env` (project root) | **Yes** | Neo4j, logging — backend only |
| `frontend/.env.production` | Only Pattern B | `VITE_API_URL` at build time |
| `frontend/.env.example` | Reference | Documents optional frontend vars |

**Never put `NEO4J_*` or other secrets in frontend env** — the browser can read them.

---

## Build & run

```bash
git clone https://github.com/HekmaAI/ehr-data.git
cd ehr-data
git checkout develop

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm ci && npm run build && cd ..

# Start (production)
uvicorn app.main:app --host 0.0.0.0 --port 8002 --workers 2
```

Open: `http://<host>:8002`  
Health check: `GET /health` → expect `"neo4j": true`

---

## Neo4j setup (one-time, before first use)

App will not work until Neo4j has data.

```bash
source .venv/bin/activate

# 1. Create schema
python -m ingestion.cli init-schema

# 2. Load FHIR data (provide bundle path on server or restore DB backup)
python -m ingestion.cli load /path/to/fhir/bundles --workers 4

# 3. Verify
python scripts/verify_ingestion.py
```

**Alternative:** Restore a Neo4j backup instead of running ingest.

Neo4j Bolt (`7687`) must be reachable from the app server only — not public.

---

## Reverse proxy (nginx example)

```nginx
server {
    listen 443 ssl;
    server_name ehr.example.com;

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Health & monitoring

| Check | URL | Pass |
|-------|-----|------|
| Liveness | `GET /health` | HTTP 200 |
| Ready | `GET /health` | `"neo4j": true` |

Watch: Neo4j memory, API response time, disk on Neo4j volume.

---

## Security (action required)

| Item | Status today | DevOps action |
|------|--------------|---------------|
| Auth | None | Add SSO / API gateway before public access |
| CORS | Open (`*`) | Restrict to portal domain |
| Neo4j | Private only | Firewall + strong password |
| TLS | Not in app | Terminate at nginx / load balancer |

---

## Ports

| Service | Port | Public? |
|---------|------|---------|
| App (Uvicorn) | 8002 | Yes (via proxy) |
| Neo4j Bolt | 7687 | No |
| Neo4j Browser | 7474 | Admin only |

---

## CI/CD checklist

- [ ] Clone `develop` branch
- [ ] `pip install -r requirements.txt`
- [ ] `cd frontend && npm ci && npm run build`
- [ ] Inject secrets (`.env` / vault)
- [ ] Deploy & start Uvicorn
- [ ] Smoke test `GET /health`
- [ ] Neo4j ingest or restore (separate job, not every deploy)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `/health` shows `neo4j: false` | Check `NEO4J_URI`, credentials, firewall to Neo4j |
| Blank UI | Run `npm run build` — `frontend/dist/` must exist |
| Broken logo / missing `/hekma-logo.svg` | Redeploy after backend fix — Uvicorn must serve files from `frontend/dist/`, not only `/assets/` |
| Empty search/graph | Run ingest or restore Neo4j data |
| 502 from proxy | Confirm Uvicorn running on port 8002 |

---

## Docs

- Setup details: `README.md`
- Architecture: `ARCHITECTURE.md`
- Ingestion tuning: `docs/INGESTION_PERFORMANCE.md`
