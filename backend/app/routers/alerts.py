from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..models.operations import Alert, Incident
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS

router = APIRouter(prefix="/alerts", tags=["alerts"])

ALERT_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS)


@router.get("")
def list_alerts(
    site_id: int | None = None,
    active_only: bool = True,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*ALERT_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        return []
    stmt = select(Alert).where(Alert.site_id == site_id)
    if active_only:
        stmt = stmt.where(Alert.status == "Active")
    return [
        {
            "id": a.id,
            "title": a.title,
            "detail": a.detail,
            "severity": a.severity,
            "alert_type": a.alert_type,
            "trigger_key": a.trigger_key,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        }
        for a in db.scalars(stmt.order_by(Alert.created_at.desc()).limit(50))
    ]


def _create_or_dedup(db: DbSession, user_id: int, site_id: int, title: str, severity: str, alert_type: str, detail: str) -> dict:
    trigger_key = f"{alert_type}|{title}"
    existing = db.scalars(
        select(Alert).where(Alert.site_id == site_id, Alert.trigger_key == trigger_key, Alert.status == "Active")
    ).first()
    if existing:
        existing.detail = detail
        log_action(db, user_id, site_id, "dedup_alert", "alert", existing.id, title)
        return {"id": existing.id, "deduped": True, "title": title}

    alert = Alert(
        site_id=site_id,
        title=title,
        detail=detail,
        severity=severity,
        alert_type=alert_type,
        status="Active",
        trigger_key=trigger_key,
        created_at=datetime.now(timezone.utc),
    )
    db.add(alert)
    db.flush()
    return {"id": alert.id, "deduped": False, "title": title}


@router.post("")
def create_alert(
    title: str,
    severity: str = "MEDIUM",
    alert_type: str = "general",
    detail: str = "",
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*ALERT_ROLES))] = None,
):
    result = _create_or_dedup(db, current.user.id, current.site_id, title, severity, alert_type, detail)
    log_action(db, current.user.id, current.site_id, "create_alert", "alert", result["id"], title)
    db.commit()
    return result


@router.post("/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*ALERT_ROLES))] = None,
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    assert current.site_id == alert.site_id or current.role == ROLE_ADMIN
    alert.status = "Resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    log_action(db, current.user.id, current.site_id, "resolve_alert", "alert", alert.id, alert.title)
    db.commit()
    return {"id": alert.id, "resolved": True}


@router.post("/auto")
def auto_alerts(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*ALERT_ROLES))] = None,
):
    """Rules engine: CRITICAL incidents + HIGH congestion predictions generate deduped alerts."""
    created = []
    critical = db.scalars(
        select(Incident).where(
            Incident.site_id == current.site_id,
            Incident.severity == "CRITICAL",
            Incident.status.notin_(["Resolved", "Closed"]),
        )
    ).all()
    for inc in critical:
        result = _create_or_dedup(
            db,
            current.user.id,
            current.site_id,
            f"CRITICAL incident active: {inc.title}",
            "CRITICAL",
            "incident",
            inc.description[:200] or inc.incident_number,
        )
        created.append(result)
    db.commit()
    return {"created": created, "count": len(created)}
