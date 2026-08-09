from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..models.operations import Incident
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS

router = APIRouter(prefix="/incidents", tags=["incidents"])

READ_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS)
RESOLVED_STATUSES = ("Resolved", "Closed")


def _next_incident_number(db: DbSession) -> str:
    count = db.scalar(select(func.count(Incident.id))) or 0
    return f"INC-{count + 1:05d}"


@router.get("")
def list_incidents(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*READ_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        return []
    return [
        {
            "id": i.id,
            "incident_number": i.incident_number,
            "category": i.category,
            "title": i.title,
            "description": i.description,
            "severity": i.severity,
            "status": i.status,
            "location": i.location,
            "assigned_to": i.assigned_to,
            "source": i.source,
            "escalation_logged": i.escalation_logged,
            "reported_at": i.reported_at.isoformat(),
            "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
        }
        for i in db.scalars(select(Incident).where(Incident.site_id == site_id).order_by(Incident.reported_at.desc()).limit(50))
    ]


@router.get("/{incident_id}")
def get_incident(
    incident_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*READ_ROLES))] = None,
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != incident.site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    return {
        "id": incident.id,
        "incident_number": incident.incident_number,
        "category": incident.category,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "status": incident.status,
        "location": incident.location,
        "assigned_to": incident.assigned_to,
        "source": incident.source,
        "escalation_logged": incident.escalation_logged,
        "reported_by": incident.reported_by,
        "reported_at": incident.reported_at.isoformat(),
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
    }


@router.post("")
def create_incident(
    category: str,
    title: str,
    description: str,
    severity: str = "MEDIUM",
    location: str | None = None,
    assigned_to: str | None = None,
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*READ_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    incident = Incident(
        site_id=site_id,
        incident_number=_next_incident_number(db),
        category=category,
        title=title,
        description=description,
        severity=severity,
        status="Reported",
        location=location,
        assigned_to=assigned_to,
        reported_by=current.user.email,
        source="Staff",
        reported_at=datetime.now(),
    )
    db.add(incident)
    db.flush()
    log_action(db, current.user.id, site_id, "create_incident", "incident", incident.id, title)
    db.commit()
    db.refresh(incident)
    return {"id": incident.id, "incident_number": incident.incident_number, "title": incident.title, "status": incident.status}


def _escalation_reason(incident: Incident) -> str | None:
    now = datetime.now()
    if incident.status not in RESOLVED_STATUSES and incident.reported_at:
        elapsed = (now - incident.reported_at).total_seconds() / 3600
        if incident.severity == "CRITICAL" and elapsed > 2:
            return f"CRITICAL open longer than 2h ({elapsed:.1f}h)"
        if incident.severity == "HIGH" and elapsed > 4:
            return f"HIGH open longer than 4h ({elapsed:.1f}h)"
    return None


@router.post("/{incident_id}/escalate")
def escalate_incident(
    incident_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_OPS))] = None,
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    assert current.site_id == incident.site_id or current.role == ROLE_ADMIN
    reason = _escalation_reason(incident)
    if not reason:
        raise HTTPException(status_code=409, detail="Incident does not meet the escalation threshold")
    incident.escalation_logged = True
    incident.assigned_at = datetime.now()
    log_action(db, current.user.id, current.site_id, "escalate_incident", "incident", incident.id, reason)
    db.commit()
    return {"id": incident.id, "escalation_logged": True, "reason": reason}


@router.post("/{incident_id}/resolve")
def resolve_incident(
    incident_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*READ_ROLES))] = None,
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    assert current.site_id == incident.site_id or current.role == ROLE_ADMIN
    incident.status = "Resolved"
    incident.resolved_at = datetime.now()
    log_action(db, current.user.id, current.site_id, "resolve_incident", "incident", incident.id, incident.title)
    db.commit()
    return {"id": incident.id, "status": incident.status}
