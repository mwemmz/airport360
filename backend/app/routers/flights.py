from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..models.operations import Flight
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS, ROLE_PASSENGER, ROLE_STAFF

router = APIRouter(prefix="/flights", tags=["flights"])

READ_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS, ROLE_STAFF, ROLE_PASSENGER)


@router.get("")
def list_flights(
    site_id: int | None = None,
    search: str | None = None,
    status: str | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*READ_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    stmt = select(Flight).where(Flight.site_id == site_id)
    if search:
        like = f"%{search.upper()}%"
        stmt = stmt.where((Flight.flight_number.like(like)) | (Flight.origin.like(like)) | (Flight.destination.like(like)))
    if status:
        stmt = stmt.where(Flight.status == status)
    return [
        {
            "id": f.id,
            "flight_number": f.flight_number,
            "airline": f.airline,
            "origin": f.origin,
            "destination": f.destination,
            "scheduled_departure": f.scheduled_departure.isoformat(),
            "scheduled_arrival": f.scheduled_arrival.isoformat(),
            "status": f.status,
            "gate": f.gate,
            "terminal": f.terminal,
            "passengers_booked": f.passengers_booked,
        }
        for f in db.scalars(stmt.order_by(Flight.scheduled_departure).limit(50))
    ]


@router.patch("/{flight_id}/status")
def update_flight_status(
    flight_id: int,
    status: str,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_OPS))] = None,
):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    assert_site_access(current, flight.site_id)
    flight.status = status
    if status == "Departed":
        flight.actual_departure = datetime.now(timezone.utc)
    if status == "Arrived":
        flight.actual_arrival = datetime.now(timezone.utc)
    log_action(db, current.user.id, current.site_id, "update_flight_status", "flight", flight.id, f"{flight.flight_number} → {status}")
    db.commit()
    return {"id": flight.id, "flight_number": flight.flight_number, "status": flight.status}
