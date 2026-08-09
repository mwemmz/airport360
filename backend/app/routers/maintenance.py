from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..models.operations import MaintenanceRequest
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS, ROLE_STAFF

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

MNT_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS, ROLE_STAFF)
RESOLVED_STATUSES = ("Resolved", "Closed")


def _next_request_number(db: DbSession) -> str:
    count = db.scalar(select(func.count(MaintenanceRequest.id))) or 0
    return f"MTN-{count + 1:05d}"


def _repeat_key(db: DbSession, site_id: int, category: str, location: str) -> str:
    key = f"{category.lower()}|{location.lower()}"
    past_resolved = db.scalar(
        select(func.count(MaintenanceRequest.id)).where(
            MaintenanceRequest.site_id == site_id,
            MaintenanceRequest.repeat_key == key,
            MaintenanceRequest.status.in_(RESOLVED_STATUSES),
        )
    )
    return key, (past_resolved or 0)


@router.get("")
def list_requests(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*MNT_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        return []
    return [
        {
            "id": r.id,
            "request_number": r.request_number,
            "category": r.category,
            "priority": r.priority,
            "status": r.status,
            "location": r.location,
            "description": r.description,
            "technician": r.technician,
            "source": r.source,
            "cost": r.cost,
            "repeat_key": r.repeat_key,
            "reported_at": r.reported_at.isoformat(),
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        }
        for r in db.scalars(select(MaintenanceRequest).where(MaintenanceRequest.site_id == site_id).order_by(MaintenanceRequest.reported_at.desc()).limit(50))
    ]


@router.post("")
def create_request(
    category: str,
    location: str,
    priority: str = "Medium",
    description: str | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_OPS, ROLE_STAFF))] = None,
):
    key, resolved_count = _repeat_key(db, current.site_id, category, location)
    is_repeat = resolved_count >= 2
    req = MaintenanceRequest(
        site_id=current.site_id,
        request_number=_next_request_number(db),
        category=category,
        priority=priority,
        status="Reported",
        location=location,
        description=description,
        reported_by=current.user.email,
        source="Staff",
        repeat_key=key,
    )
    db.add(req)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_maintenance", "maintenance_request", req.id, f"{category} @ {location}")
    db.commit()
    db.refresh(req)
    return {
        "id": req.id,
        "request_number": req.request_number,
        "category": category,
        "status": req.status,
        "repeat_failure": is_repeat,
        "repeat_notice": "Asset flagged as repeat failure (resolved 2+ times before)" if is_repeat else None,
    }


@router.post("/{request_id}/resolve")
def resolve_request(
    request_id: int,
    technician: str | None = None,
    cost: float = 0.0,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_OPS))] = None,
):
    req = db.get(MaintenanceRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
    assert current.site_id == req.site_id or current.role == ROLE_ADMIN
    req.status = "Resolved"
    req.resolved_at = datetime.now(timezone.utc)
    req.technician = technician or req.technician
    req.cost = cost
    _, resolved_count = _repeat_key(db, req.site_id, req.category, req.location)
    is_repeat = resolved_count >= 2
    log_action(db, current.user.id, current.site_id, "resolve_maintenance", "maintenance_request", req.id, f"repeat_failure={is_repeat}")
    db.commit()
    return {"id": req.id, "status": req.status, "repeat_failure": is_repeat}


@router.get("/repeat-failures")
def repeat_failures(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*MNT_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        return []
    rows = db.execute(
        select(
            MaintenanceRequest.repeat_key,
            MaintenanceRequest.category,
            MaintenanceRequest.location,
            func.count(MaintenanceRequest.id).label("resolutions"),
        )
        .where(
            MaintenanceRequest.site_id == site_id,
            MaintenanceRequest.status.in_(RESOLVED_STATUSES),
            MaintenanceRequest.repeat_key.isnot(None),
        )
        .group_by(MaintenanceRequest.repeat_key, MaintenanceRequest.category, MaintenanceRequest.location)
        .having(func.count(MaintenanceRequest.id) >= 2)
        .order_by(func.count(MaintenanceRequest.id).desc())
    ).all()
    return [
        {
            "repeat_key": row.repeat_key,
            "category": row.category,
            "location": row.location,
            "resolutions": row.resolutions,
            "recommendation": "Asset replacement review recommended",
        }
        for row in rows
    ]
