from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .routers import audit, auth, bi, capacity_building, finance, hr, procurement, sites, users

settings = get_settings()

app = FastAPI(
    title="Airport360",
    description=(
        "Airport360 — locally-built ERP platform for a multi-site airport authority "
        "(Phase 1: HR, Procurement, Finance, Business Intelligence, Capacity Building). "
        "All data is simulated and anonymized."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "auth", "description": "Authentication and current-user identity"},
        {"name": "users", "description": "User administration (Administrator only)"},
        {"name": "sites", "description": "Airport site / tenant administration"},
        {"name": "hr", "description": "Human resources: employees, departments, training records"},
        {"name": "procurement", "description": "Requisition → approval → purchase order workflow"},
        {"name": "finance", "description": "Budgets and expenses (internal record-keeping only, no PCI scope)"},
        {"name": "bi", "description": "Cross-module business intelligence dashboards"},
        {"name": "capacity-building", "description": "Partnership capacity-building tracking"},
        {"name": "audit", "description": "Audit log of all write operations (Administrator only)"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, users, sites, hr, procurement, finance, bi, capacity_building, audit):
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
