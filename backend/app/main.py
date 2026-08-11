import logging
import threading
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import models  # noqa: F401  (import models so metadata is populated for create_all)
from .config import get_settings
from .database import Base, engine, ensure_column
from .seed import seed_all
from .routers import (
    ai,
    alerts,
    attendance,
    audit,
    auth,
    baggage,
    bi,
    bookings,
    capacity_building,
    cargo,
    complaints,
    computer_vision,
    finance,
    flights,
    hr,
    hr_cases,
    incidents,
    leave,
    maintenance,
    ops,
    passenger,
    payroll,
    predictions,
    procurement,
    queues,
    roster,
    sites,
    statutory,
    kiosk,
    travel_agencies,
    users,
)

settings = get_settings()
logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Airport360",
    description=(
        "Airport360 — locally-built ERP platform for a multi-site airport authority "
        "(Phase 1: HR, Procurement, Finance, Business Intelligence, Capacity Building; "
        "Phase 2: Operational Intelligence; Phase 3: Passenger App; Phase 4: Booking Marketplace). "
        "All data is simulated and anonymized."
    ),
    version="2.0.0",
    openapi_tags=[
        {"name": "auth", "description": "Authentication and current-user identity"},
        {"name": "users", "description": "User administration (Administrator only)"},
        {"name": "sites", "description": "Airport site / tenant administration"},
        {"name": "hr", "description": "Human resources: employees, departments, training records, leave, attendance, payroll, HR cases, shift roster, statutory config"},
        {"name": "procurement", "description": "Requisition → approval → purchase order workflow"},
        {"name": "finance", "description": "Budgets and expenses (internal record-keeping only, no PCI scope)"},
        {"name": "bi", "description": "Cross-module business intelligence dashboards"},
        {"name": "capacity-building", "description": "Partnership capacity-building tracking"},
        {"name": "audit", "description": "Audit log of all write operations (Administrator only)"},
        {"name": "ops", "description": "Command Center: operational KPIs, risk level, event timeline"},
        {"name": "flights", "description": "Flight schedule and live status"},
        {"name": "passenger", "description": "Passenger self-service: flight/baggage status, complaints"},
        {"name": "baggage", "description": "Baggage tracking and risk scoring"},
        {"name": "queues", "description": "Queue samples (recorded or CV-derived)"},
        {"name": "predictions", "description": "Queue ML predictions + model run registry"},
        {"name": "incidents", "description": "Incident reporting, escalation, resolution"},
        {"name": "maintenance", "description": "Maintenance requests and repeat-failure detection"},
        {"name": "cargo", "description": "Cargo shipment status"},
        {"name": "alerts", "description": "Alert rules engine with deduplication"},
        {"name": "ai", "description": "AI assistant: Fact/Prediction/Recommendation answers over platform data"},
        {"name": "computer-vision", "description": "Privacy-preserving crowd/queue analytics (aggregates only)"},
        {"name": "complaints", "description": "Complaints management (staff-facing)"},
        {"name": "travel-agencies", "description": "Certified travel agency partner directory"},
        {"name": "bookings", "description": "Booking marketplace referral logging and analytics"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    auth,
    users,
    sites,
    hr,
    leave,
    attendance,
    payroll,
    roster,
    hr_cases,
    statutory,
    kiosk,
    procurement,
    finance,
    bi,
    capacity_building,
    audit,
    ops,
    flights,
    passenger,
    baggage,
    queues,
    predictions,
    incidents,
    maintenance,
    cargo,
    alerts,
    ai,
    computer_vision,
    complaints,
    travel_agencies,
    bookings,
):
    app.include_router(r.router, prefix=settings.api_v1_prefix)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"Internal server error: {exc}"})


@app.get("/")
def root():
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    # Create tables synchronously so the API works as soon as the port opens.
    # Wrapped in try/except so a transient Turso outage can't crash the app at boot.
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        logger.exception(
            "create_all failed (app stays up; check TURSO_DATABASE_URL / TURSO_AUTH_TOKEN)"
        )

    # Seeding is heavy (two sites + thousands of rows over the remote Turso
    # connection); run it in a background thread so the port binds immediately
    # and Render's health scan passes. seed_all() skips when data already exists.
    threading.Thread(target=_seed_in_background, name="startup-seed", daemon=True).start()


def _seed_in_background():
    # Column patches for pre-existing databases (create_all never alters
    # existing tables, so the deployed Turso DB would keep missing newer
    # columns like users.pin_hash without this).
    for table, column, col_type in (
        ("users", "pin_hash", "VARCHAR(255)"),
        ("employees", "contract_type", "VARCHAR(24) DEFAULT 'Permanent'"),
    ):
        try:
            ensure_column(table, column, col_type)
        except Exception:
            logger.exception("ensure_column(%s.%s) failed (app stays up)", table, column)

    # Turso's HTTP streams drop long-lived transactions, so a single attempt can
    # fail partway. seed_all() commits in small batches and resets any partial
    # data on the next attempt, so retrying converges to a complete dataset.
    for attempt in range(1, 4):
        try:
            seed_all()
            return
        except Exception:
            logger.exception("background seed attempt %s of 3 failed (app stays up)", attempt)
            time.sleep(10 * attempt)
