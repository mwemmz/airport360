from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..models.operations import Complaint, Incident
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS

router = APIRouter(prefix="/complaints", tags=["complaints"])

COMPLAINT_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS)


def _next_complaint_number(db: DbSession) -> str:
    count = db.scalar(select(func.count(Complaint.id))) or 0
    return f"CMP-{count + 1:05d}"


@router.get("")
def list_complaints(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*COMPLAINT_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        return []
    return [
        {
            "id": c.id,
            "complaint_number": c.complaint_number,
            "category": c.category,
            "status": c.status,
            "title": c.title,
            "description": c.description,
            "passenger_reference": c.passenger_reference,
            "linked_incident_id": c.linked_incident_id,
            "submitted_at": c.submitted_at.isoformat(),
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        }
        for c in db.scalars(select(Complaint).where(Complaint.site_id == site_id).order_by(Complaint.submitted_at.desc()).limit(50))
    ]


@router.post("")
def submit_complaint(
    category: str,
    title: str,
    passenger_reference: str,
    description: str | None = None,
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*COMPLAINT_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    complaint = Complaint(
        site_id=site_id,
        complaint_number=_next_complaint_number(db),
        passenger_reference=passenger_reference,
        category=category,
        title=title,
        description=description,
        status="Submitted",
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(complaint)
    db.flush()
    log_action(db, current.user.id, site_id, "submit_complaint", "complaint", complaint.id, title)
    db.commit()
    db.refresh(complaint)
    return {"id": complaint.id, "complaint_number": complaint.complaint_number, "status": complaint.status}


@router.post("/{complaint_id}/resolve")
def resolve_complaint(
    complaint_id: int,
    create_incident: bool = False,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*COMPLAINT_ROLES))] = None,
):
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    assert current.site_id == complaint.site_id or current.role == ROLE_ADMIN

    incident_id = complaint.linked_incident_id
    if create_incident and not incident_id:
        incident = Incident(
            site_id=complaint.site_id,
            incident_number=f"INC-{complaint.complaint_number.split('-')[-1]}-{datetime.now().strftime('%H%M')}",
            category="passenger issue",
            severity="MEDIUM",
            status="Reported",
            title=complaint.title,
            description=complaint.description,
            reported_by=current.user.email,
            source="Passenger",
            reported_at=datetime.now(timezone.utc),
        )
        db.add(incident)
        db.flush()
        incident_id = incident.id
        complaint.linked_incident_id = incident_id

    complaint.status = "Resolved"
    complaint.resolved_at = datetime.now(timezone.utc)
    log_action(db, current.user.id, current.site_id, "resolve_complaint", "complaint", complaint.id, f"incident={incident_id}")
    db.commit()
    return {"id": complaint.id, "status": complaint.status, "linked_incident_id": incident_id}
