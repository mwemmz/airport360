from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..models.operations import (
    Alert,
    Baggage,
    CargoShipment,
    Flight,
    Incident,
    MaintenanceRequest,
    QueuePrediction,
    QueueSample,
)
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS, ROLE_STAFF

router = APIRouter(prefix="/ops", tags=["ops"])

OPS_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS)


def _compute_risk_level(db: DbSession, site_id: int) -> dict:
    """Documented rule (not hardcoded display): each condition adds a weighted score.
    >=4 CRITICAL, >=3 HIGH, >=2 MEDIUM, else LOW."""
    critical_incidents = db.scalar(
        select(func.count(Incident.id)).where(
            Incident.site_id == site_id, Incident.severity == "CRITICAL",
            Incident.status.notin_(["Resolved", "Closed"]),
        )
    ) or 0
    high_congestion = db.scalar(
        select(func.count(QueuePrediction.id)).where(
            QueuePrediction.site_id == site_id,
            QueuePrediction.congestion_level.in_(["HIGH", "CRITICAL"]),
        )
    ) or 0
    delayed_bags = db.scalar(
        select(func.count(Baggage.id)).where(
            Baggage.site_id == site_id, Baggage.status.in_(["Missing", "Delayed"]),
        )
    ) or 0
    cargo_delays = db.scalar(
        select(func.count(CargoShipment.id)).where(
            CargoShipment.site_id == site_id, CargoShipment.delayed,
        )
    ) or 0
    high_priority_maintenance = db.scalar(
        select(func.count(MaintenanceRequest.id)).where(
            MaintenanceRequest.site_id == site_id, MaintenanceRequest.priority == "High",
            MaintenanceRequest.status.notin_(["Resolved", "Closed"]),
        )
    ) or 0

    score = (
        min(4, critical_incidents) * 2
        + min(2, high_congestion) * 1
        + min(2, delayed_bags) * 1
        + min(2, cargo_delays) * 1
        + min(2, high_priority_maintenance) * 1
    )
    level = "CRITICAL" if score >= 5 else "HIGH" if score >= 3 else "MEDIUM" if score >= 2 else "LOW"
    return {
        "level": level,
        "score": score,
        "rule": "critical_incidents*2 + high_congestion + delayed_bags + cargo_delays + high_priority_maintenance; >=5 CRITICAL, >=3 HIGH, >=2 MEDIUM, else LOW",
        "components": {
            "critical_incidents": critical_incidents,
            "high_congestion_predictions": high_congestion,
            "delayed_bags": delayed_bags,
            "cargo_delays": cargo_delays,
            "high_priority_maintenance": high_priority_maintenance,
        },
    }


def _timeline(db: DbSession, site_id: int, limit: int = 30) -> list[dict]:
    events: list[dict] = []

    for alert in db.scalars(select(Alert).where(Alert.site_id == site_id).order_by(Alert.created_at.desc()).limit(limit)):
        events.append({"ts": alert.created_at, "kind": "alert", "severity": alert.severity, "title": alert.title, "detail": alert.detail})

    for inc in db.scalars(select(Incident).where(Incident.site_id == site_id).order_by(Incident.reported_at.desc()).limit(limit)):
        events.append({"ts": inc.reported_at, "kind": "incident", "severity": inc.severity, "title": inc.title, "detail": f"status={inc.status}"})

    for fl in db.scalars(select(Flight).where(Flight.site_id == site_id).order_by(Flight.scheduled_departure.desc()).limit(limit)):
        events.append({"ts": fl.scheduled_departure, "kind": "flight", "severity": None, "title": f"{fl.flight_number} {fl.status}", "detail": f"{fl.origin}→{fl.destination}"})

    for pred in db.scalars(select(QueuePrediction).where(QueuePrediction.site_id == site_id).order_by(QueuePrediction.created_at.desc()).limit(limit)):
        events.append({"ts": pred.created_at, "kind": "prediction", "severity": pred.congestion_level, "title": f"{pred.queue_type} queue forecast", "detail": f"{pred.predicted_length} people @ +{pred.horizon_minutes}min"})

    events.sort(key=lambda e: e["ts"], reverse=True)
    return [{"ts": e["ts"].isoformat(), "kind": e["kind"], "severity": e["severity"], "title": e["title"], "detail": e["detail"]} for e in events[: limit]]


@router.get("/overview")
def overview(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*OPS_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)

    passenger_count = db.scalar(select(func.sum(Flight.passengers_booked)).where(Flight.site_id == site_id)) or 0
    current_queues = db.scalars(
        select(QueueSample).where(QueueSample.site_id == site_id).order_by(QueueSample.recorded_at.desc()).limit(6)
    ).all()
    avg_wait = db.scalar(select(func.avg(QueueSample.avg_wait_minutes)).where(QueueSample.site_id == site_id)) or 0
    active_incidents = db.scalar(
        select(func.count(Incident.id)).where(Incident.site_id == site_id, Incident.status.notin_(["Resolved", "Closed"]))
    ) or 0
    open_maintenance = db.scalar(
        select(func.count(MaintenanceRequest.id)).where(
            MaintenanceRequest.site_id == site_id, MaintenanceRequest.status.notin_(["Resolved", "Closed"])
        )
    ) or 0
    baggage_exceptions = db.scalar(
        select(func.count(Baggage.id)).where(
            Baggage.site_id == site_id, Baggage.exception_type.isnot(None)
        )
    ) or 0
    cargo_in_processing = db.scalar(
        select(func.count(CargoShipment.id)).where(
            CargoShipment.site_id == site_id, CargoShipment.status.notin_(["Released", "Delivered"])
        )
    ) or 0
    flights = db.scalars(select(Flight).where(Flight.site_id == site_id).order_by(Flight.scheduled_departure).limit(8)).all()

    return {
        "site_id": site_id,
        "passenger_count": int(passenger_count),
        "current_queue_length": round(sum(q.current_length for q in current_queues) / max(1, len(current_queues)), 1),
        "avg_wait_minutes": round(float(avg_wait), 1),
        "active_incidents": active_incidents,
        "open_maintenance": open_maintenance,
        "baggage_exceptions": baggage_exceptions,
        "cargo_in_processing": cargo_in_processing,
        "flights": [
            {
                "flight_number": f.flight_number,
                "airline": f.airline,
                "origin": f.origin,
                "destination": f.destination,
                "scheduled_departure": f.scheduled_departure.isoformat(),
                "status": f.status,
                "gate": f.gate,
            }
            for f in flights
        ],
        "risk_level": _compute_risk_level(db, site_id),
        "timeline": _timeline(db, site_id),
        "label": "Simulated operational data",
    }


@router.get("/timeline")
def timeline(
    site_id: int | None = None,
    limit: int = 30,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*OPS_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    return _timeline(db, site_id, limit)
