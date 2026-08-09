from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..deps import CurrentUser, DbSession, require_roles
from ..models.operations import Baggage, BaggageScan, Complaint, Flight, Passenger
from ..security import ROLE_PASSENGER

router = APIRouter(prefix="/passenger", tags=["passenger"])


@router.get("/flight-status")
def flight_status(
    reference: str,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_PASSENGER))] = None,
):
    flight = db.scalar(
        select(Flight).join(Passenger, Passenger.flight_id == Flight.id).where(
            Passenger.site_id == current.site_id,
            Passenger.passenger_reference == reference.upper(),
        )
    )
    if not flight:
        raise HTTPException(status_code=404, detail="No flight found for that passenger reference")
    return {
        "flight_number": flight.flight_number,
        "airline": flight.airline,
        "origin": flight.origin,
        "destination": flight.destination,
        "scheduled_departure": flight.scheduled_departure.isoformat(),
        "status": flight.status,
        "gate": flight.gate,
        "terminal": flight.terminal,
    }


@router.get("/baggage")
def baggage_status(
    reference: str,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_PASSENGER))] = None,
):
    bags = db.scalars(
        select(Baggage).where(
            Baggage.site_id == current.site_id,
            Baggage.passenger_reference == reference.upper(),
        )
    ).all()
    if not bags:
        raise HTTPException(status_code=404, detail="No baggage found for that passenger reference")
    result = []
    for bag in bags:
        scans = db.scalars(
            select(BaggageScan).where(BaggageScan.baggage_id == bag.id).order_by(BaggageScan.scanned_at)
        ).all()
        result.append({
            "bag_id": bag.bag_id,
            "status": bag.status,
            "current_location": bag.current_location,
            "exception_type": bag.exception_type,
            "history": [
                {"event": s.scan_event, "location": s.location, "at": s.scanned_at.isoformat()}
                for s in scans
            ],
        })
    return result


@router.post("/complaints")
def submit_complaint(
    category: str,
    title: str,
    reference: str,
    description: str | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_PASSENGER))] = None,
):
    from ..audit import log_action
    from ..models.operations import Complaint
    from sqlalchemy import func

    count = db.scalar(select(func.count(Complaint.id))) or 0
    complaint = Complaint(
        site_id=current.site_id,
        complaint_number=f"CMP-{count + 1:05d}",
        passenger_reference=reference.upper(),
        category=category,
        title=title,
        description=description,
        status="Submitted",
    )
    db.add(complaint)
    db.flush()
    log_action(db, current.user.id, current.site_id, "passenger_submit_complaint", "complaint", complaint.id, title)
    db.commit()
    db.refresh(complaint)
    return {"id": complaint.id, "complaint_number": complaint.complaint_number, "status": complaint.status}
