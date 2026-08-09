from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..models.operations import BookingReferral, TravelAgencyPartner
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS, ROLE_PASSENGER

router = APIRouter(prefix="/bookings", tags=["bookings"])

BOOKING_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS, ROLE_PASSENGER)


@router.get("/partners")
def partners(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*BOOKING_ROLES))] = None,
):
    return [
        {
            "id": p.id,
            "name": p.name,
            "website": p.website,
            "certified": p.certified,
            "security_endorsed": p.security_endorsed,
        }
        for p in db.scalars(select(TravelAgencyPartner).where(TravelAgencyPartner.active.is_(True)).order_by(TravelAgencyPartner.name))
    ]


@router.post("/referrals")
def log_referral(
    partner_id: int,
    airline: str,
    origin: str,
    destination: str,
    passenger_reference: str,
    redirect_url: str,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*BOOKING_ROLES))] = None,
):
    partner = db.get(TravelAgencyPartner, partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    if not redirect_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="redirect_url must be https")

    referral = BookingReferral(
        site_id=current.site_id,
        passenger_reference=passenger_reference.upper(),
        partner_id=partner.id,
        airline=airline,
        flight_search={"origin": origin, "destination": destination},
        redirect_url=redirect_url,
        commission_estimate=partner.commission_rate,
    )
    db.add(referral)
    db.flush()
    log_action(db, current.user.id, current.site_id, "log_booking_referral", "booking_referral", referral.id, f"{airline} {origin}→{destination}")
    db.commit()
    db.refresh(referral)
    return {
        "id": referral.id,
        "partner_id": partner.id,
        "redirect_url": redirect_url,
        "commission_estimate": partner.commission_rate,
        "clicked_at": referral.clicked_at.isoformat(),
    }


@router.get("/analytics")
def analytics(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE))] = None,
):
    if site_id is None:
        site_id = current.site_id
    total = db.scalar(select(func.count(BookingReferral.id)).where(BookingReferral.site_id == site_id)) or 0
    est_commission = db.scalar(select(func.sum(BookingReferral.commission_estimate)).where(BookingReferral.site_id == site_id)) or 0
    by_partner = db.execute(
        select(TravelAgencyPartner.name, func.count(BookingReferral.id))
        .join(BookingReferral, BookingReferral.partner_id == TravelAgencyPartner.id)
        .where(BookingReferral.site_id == site_id)
        .group_by(TravelAgencyPartner.name)
        .order_by(func.count(BookingReferral.id).desc())
    ).all()
    return {
        "total_referrals": total,
        "estimated_commission": round(float(est_commission), 2),
        "by_partner": [{"partner": row[0], "referrals": row[1]} for row in by_partner],
        "tag": "Referral analytics — commission estimates only, no PNR/payment data",
    }
