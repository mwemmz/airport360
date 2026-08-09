# Airport360 — ZACL Digital Transformation Platform

A modular, locally-built digital-transformation platform for a multi-site airport authority.
This repository implements **Phase 1 (Core ERP)** as a genuinely complete, demoable system:

**HR · Procurement · Finance · Business Intelligence · Capacity Building**

All data is **simulated and anonymized**. No real airport systems, restricted databases,
or biometric data are involved. No production-certification claims are made.

## Scope boundaries

- **Multi-site is a Phase 1 requirement** — every site-scoped record carries `site_id → sites.id`
  from the first migration onward.
- **Finance is internal record-keeping only** — no payment processing, no PCI-DSS scope.
- **BI anomaly flags are rule-based** (spend > 2.5× site average for its category) and are labeled
  as such in the UI — this is where the partnership's "AI" language first lands in something
  low-risk and legible.

## Stack

| Layer     | Tech |
|-----------|------|
| Frontend  | React + Vite + TypeScript + Tailwind CSS + Recharts |
| Backend   | Python + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + JWT + API-layer RBAC |
| Database  | PostgreSQL (prod) / SQLite (dev) via the same models, env-driven |
| Migrations| Alembic |
| Testing   | pytest + httpx (backend); Vitest + RTL (frontend) |
| Dev/Ops   | Docker + docker-compose (one command boots the demo) |

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
| `hr.nm@airport360.com` | HR Officer | 2 (Namwala) |

Use the HR Officer at site 1 and site 2 together to see **site isolation** in action.

## Phase 1 exit criteria (from the source build prompt)

> A user can log in, get correctly scoped to their role and site, submit and approve a
> requisition end-to-end through the real API, see it reflected in Finance and BI dashboards
> with no hardcoded numbers, and an Administrator can view the audit log of that entire flow.

## Tests

```bash
cd backend
python -m pytest tests -q
```

Tests cover: auth, the full requisition→approval→PO→receipt flow via the real API, RBAC
rejections, and an explicit **cross-site data isolation** test asserting no query path returns
another site's data.

## Security (Phase 1 scope)

- JWT auth + bcrypt-hashed passwords
- RBAC enforced at the API layer (`deps.require_roles`) — every endpoint independently
  returns 403 for out-of-role or out-of-site callers
- Site isolation: a request resolves to exactly its own site unless the caller is an
  Administrator or Executive (explicitly authorized cross-site set)
- Audit logging on **all** writes (HR / Finance / Procurement)
- CORS explicitly configured (never wildcarded), env-based secrets, `.env` gitignored
- No biometric data stored; no real operator data consumed

## API structure (`/v1`)

`/auth` `/users` `/sites` `/hr` `/procurement` `/finance` `/bi` `/capacity-building` `/audit`

## Roadmap (not built — per source prompt)

- **Phase 2** — Operational Intelligence: ops command center, privacy-preserving crowd CV
  (no facial recognition), queue prediction (scikit-learn, metrics stored in `model_runs`),
  baggage intelligence, incidents, maintenance, CargoFlow, alerts, AI assistant +
  recommendations. Every AI output labeled as a prototype prediction from simulated data.
- **Phase 3** — Passenger-facing app (search/status, reporting into the same incident and
  maintenance tables).
- **Phase 4** — Affiliate flight search / travel-agency marketplace (referral logging only,
  no payments or PNR storage).

## Design decisions

- **Anomaly rule (2.5× site-average spend):** a transparent, explainable "first AI landing"
  chosen over a black-box model because the BI dashboard is likely shown to non-technical
  stakeholders first. The rule and its inputs are returned with every flag.
- **Single auth dependency pattern:** `require_roles(...)` + `assert_site_access(...)` keep
  both role checks and site checks on every site-scoped route.
- **Seed history (≈8 weeks)**: enough spend/training history for BI trends to be real rather
  than visually invented.
