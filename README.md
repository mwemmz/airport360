# Airport360 — ZACL Digital Transformation Platform

A modular, locally-built digital-transformation platform for a multi-site airport authority.
This repository implements **Phases 1–4** as a genuinely complete, demoable system:

**HR · Procurement · Finance · Business Intelligence · Capacity Building ·
Operational Intelligence · Passenger App · Booking Marketplace**

All data is **simulated and anonymized**. No real airport systems, restricted databases,
or biometric data are involved. No production-certification claims are made.

## Scope boundaries

- **Multi-site is a core requirement** — every site-scoped record carries `site_id → sites.id`
  from the first migration onward.
- **Finance is internal record-keeping only** — no payment processing, no PCI-DSS scope.
- **BI anomaly flags are rule-based** (spend > 2.5× site average for its category) and are labeled
  as such in the UI.
- **Queue predictions / baggage risk are prototype models** trained on simulated data; every AI
  output is labeled as a prediction and metrics are stored per model run (`model_runs`).
- **Computer vision is privacy-preserving by design** — HOG person detection returns aggregate
  counts only; frames/videos are processed in-memory or from a temp dir and deleted, never stored,
  never linked to passenger records, no facial recognition.
- **Booking marketplace is referral logging only** — no PNR, no payment data, booking happens on
  the airline's own checkout.

## Stack

| Layer     | Tech |
|-----------|------|
| Frontend  | React + Vite + TypeScript + Tailwind CSS + Recharts (mobile-first: drawer nav, responsive tables) |
| Backend   | Python + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + JWT + API-layer RBAC + scikit-learn + OpenCV |
| Database  | PostgreSQL (prod) / SQLite (dev) / Turso (libSQL, Render deploy) via the same models, env-driven |
| Migrations| Alembic |
| Testing   | pytest + httpx (backend) |
| Dev/Ops   | Docker + docker-compose (one command boots the demo); Render + Turso blueprint (`render.yaml`) |

## Quick start (local dev)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
python -m app.seed                # seeds 2 sites of simulated data
uvicorn app.main:app --reload     # http://localhost:8000/docs

# Frontend (new terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

The Vite dev server proxies `/v1` to `http://localhost:8000`.

## Quick start (Docker — one command)

```bash
docker compose up --build
```

- Frontend: http://localhost:8080
- API + OpenAPI docs: http://localhost:8000/docs

## Demo accounts

Password for all seeded accounts: `Demo1234!`

| Email | Role | Site |
|-------|------|------|
| `admin.ku@airport360.com` | Administrator | 1 (Kuomboka) |
| `executive.ku@airport360.com` | Executive (cross-site, read-only) | 1 |
| `hr.ku@airport360.com` | HR Officer | 1 |
| `finance.ku@airport360.com` | Finance Officer | 1 |
| `depthead.ku@airport360.com` | Department Head / Approver | 1 |
| `staff.ku@airport360.com` | Staff | 1 |
| `ops.ku@airport360.com` | Operations Manager | 1 |
| `passenger.ku@airport360.com` | Passenger | 1 |
| `hr.nm@airport360.com` | HR Officer | 2 (Namwala) |
| `ops.nm@airport360.com` | Operations Manager | 2 (Namwala) |

Use the HR Officer or Operations Manager at site 1 and site 2 together to see **site isolation**
in action.

## Modules & demo flows

- **Phase 1 (Core ERP)** — HR, Procurement (requisition → approval → PO → receipt), Finance
  (budgets/expenses), BI dashboards (rule-based anomaly flags), Capacity Building, Audit log.
- **Phase 2 (Operational Intelligence)** — Command Center (KPIs, risk level with a documented rule,
  merged event timeline), flights, queue samples + `LinearRegression` queue predictions with stored
  model metrics, baggage risk scoring, incidents with escalation rules (CRITICAL > 2h, HIGH > 4h),
  maintenance with repeat-failure detection, cargo, alerts rules engine with dedup, AI assistant
  (Fact/Prediction/Recommendation over platform data), privacy-preserving video crowd analytics.
- **Phase 3 (Passenger App)** — flight status, baggage tracking history, complaint submission that
  reports into the same incident tables.
- **Phase 4 (Booking Marketplace)** — certified travel-agency directory and referral logging with
  commission estimates and analytics (no payments, no PNR).

## Tests

```bash
cd backend
python -m pytest tests -q
```

Tests cover: auth, the full requisition→approval→PO→receipt flow via the real API, RBAC
rejections, cross-site isolation, queue prediction + model-run metrics, baggage risk bounds,
incident escalation thresholds, maintenance repeat-failure detection, alert deduplication,
complaint→incident linking, booking referral validation, and the passenger self-service flow.

## Deployment (Render + Turso)

Render (Linux) + Turso (libSQL edge database) is the supported production path. The driver is
`sqlalchemy-libsql` — **Linux/macOS only**, so it lives in `requirements-turso.txt` and is never
installed on Windows dev machines.

1. **Create a Turso database** and copy its URL + auth token:
   ```bash
   turso db create airport360
   turso db show airport360 --url
   turso db tokens create airport360
   ```
2. **Push the repo to GitHub**, then in the Render dashboard choose **Blueprint** and select
   `render.yaml`. Two services are created:
   - `airport360-api` (web service) — installs both requirements files, runs
     `alembic upgrade head`, seeds demo data, serves Uvicorn on `$PORT`.
   - `airport360-frontend` (static site) — builds with `VITE_API_URL` = backend URL, with an SPA
     rewrite to `/index.html`.
3. **Set secrets** on the API service:
   - `DATABASE_URL` → `sqlite+libsql://<your-db>-<org>.turso.io?secure=true`
   - `TURSO_AUTH_TOKEN` → the token from step 1
   - `CORS_ORIGINS` → `["https://<your-frontend>.onrender.com"]`
4. Open the frontend URL and log in with any demo account.

Deploying on Windows locally against Turso is not supported (driver build fails on Windows) —
local development always uses SQLite via `requirements.txt`.

## Security

- JWT auth + bcrypt-hashed passwords
- RBAC enforced at the API layer (`deps.require_roles`) — every endpoint independently
  returns 403 for out-of-role or out-of-site callers
- Site isolation: a request resolves to exactly its own site unless the caller is an
  Administrator or Executive (explicitly authorized cross-site set)
- Audit logging on **all** writes (HR / Finance / Procurement / Ops / Passenger / Bookings)
- CORS explicitly configured (never wildcarded), env-based secrets, `.env` gitignored
- No biometric data stored; no real operator data consumed; CV retains aggregates only

## API structure (`/v1`)

`/auth` `/users` `/sites` `/hr` `/procurement` `/finance` `/bi` `/capacity-building` `/audit`
`/ops` `/flights` `/queues` `/predictions` `/baggage` `/incidents` `/maintenance` `/cargo`
`/alerts` `/ai` `/computer-vision` `/passenger` `/complaints` `/travel-agencies` `/bookings`

## Design decisions

- **Anomaly rule (2.5× site-average spend)** and the **ops risk rule** are transparent and
  explainable — the rules and their inputs are returned with every flag, because these dashboards
  are likely shown to non-technical stakeholders first.
- **Model versioning**: every queue prediction stores the run (`model_runs`) and its metrics, so
  "accuracy: X%" claims in the UI are always traceable to a real run.
- **Privacy first for CV**: the system only ever persists aggregate crowd metrics, never frames.
- **Mobile-first UI**: drawer navigation below the `md` breakpoint, responsive stat grids, and
  horizontally scrollable tables that never break the layout on phones.
- **Single auth dependency pattern:** `require_roles(...)` + `assert_site_access(...)` keep
  both role checks and site checks on every site-scoped route.
- **Seed history (≈8 weeks, 42 queue samples/site)**: enough spend, queue and flight history for
  BI trends and the queue model to be real rather than visually invented.
