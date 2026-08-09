from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from ..deps import CurrentUser, DbSession, require_roles
from ..ml.baggage_risk import score_baggage
from ..models.operations import Baggage, BaggageScan, Flight
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS

router = APIRouter(prefix="/baggage", tags=["baggage"])

BAG_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS)


@router.get("")
def list_baggage(
    site_id: int | None = None,
    high_risk_only: bool = False,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*BAG_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        return []

    bags = db.scalars(select(Baggage).where(Baggage.site_id == site_id)).all()
    flights = {f.id: f for f in db.scalars(select(Flight).where(Flight.site_id == site_id))}

    rows = []
    for bag in bags:
        scans = db.scalars(select(BaggageScan).where(BaggageScan.baggage_id == bag.id).order_by(BaggageScan.scanned_at)).all()
        latest_scan = scans[-1].scanned_at if scans else None
        workload = sum(1 for b in bags if b.status in ("Processing", "Transferring"))
        risk = score_baggage(bag, latest_scan, scans, transfer_workload=workload)
        if high_risk_only and risk.risk_score < 0.5:
            continue
        flight = flights.get(bag.flight_id) if bag.flight_id else None
        rows.append({
            "id": bag.id,
            "bag_id": bag.bag_id,
            "passenger_reference": bag.passenger_reference,
            "flight_number": flight.flight_number if flight else None,
            "origin": bag.origin,
            "destination": bag.destination,
            "status": bag.status,
            "current_location": bag.current_location,
            "exception_type": bag.exception_type,
            "transfer_time_minutes": bag.transfer_time_minutes,
            "risk_score": risk.risk_score,
            "risk_reasons": risk.reasons,
            "risk_label": risk.model_label,
            "tag": "Prototype risk model — not validated against real mishandling data",
        })
    rows.sort(key=lambda r: r["risk_score"], reverse=True)
    return rows


@router.get("/high-risk")
def high_risk(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*BAG_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        return []
    bags = db.scalars(select(Baggage).where(Baggage.site_id == site_id)).all()
    flights = {f.id: f for f in db.scalars(select(Flight).where(Flight.site_id == site_id))}
    rows = []
    for bag in bags:
        scans = db.scalars(select(BaggageScan).where(BaggageScan.baggage_id == bag.id)).all()
        latest_scan = scans[-1].scanned_at if scans else None
        workload = sum(1 for b in bags if b.status in ("Processing", "Transferring"))
        risk = score_baggage(bag, latest_scan, scans, transfer_workload=workload)
        if risk.risk_score >= 0.5:
            flight = flights.get(bag.flight_id) if bag.flight_id else None
            rows.append({
                "bag_id": bag.bag_id,
                "flight_number": flight.flight_number if flight else None,
                "status": bag.status,
                "risk_score": risk.risk_score,
                "risk_reasons": risk.reasons,
                "risk_label": risk.model_label,
            })
    rows.sort(key=lambda r: r["risk_score"], reverse=True)
    return rows
