from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..models.operations import TravelAgencyPartner
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS, ROLE_PASSENGER

router = APIRouter(prefix="/travel-agencies", tags=["travel-agencies"])

MANAGE_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE)


@router.get("")
def list_partners(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*MANAGE_ROLES, ROLE_OPS, ROLE_PASSENGER))] = None,
):
    return [
        {
            "id": p.id,
            "name": p.name,
            "website": p.website,
            "certified": p.certified,
            "security_endorsed": p.security_endorsed,
            "commission_rate": p.commission_rate,
            "active": p.active,
        }
        for p in db.scalars(select(TravelAgencyPartner).where(TravelAgencyPartner.active.is_(True)).order_by(TravelAgencyPartner.name))
    ]


@router.post("")
def add_partner(
    name: str,
    website: str,
    commission_rate: float = 0.0,
    certified: bool = False,
    security_endorsed: bool = False,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*MANAGE_ROLES))] = None,
):
    partner = TravelAgencyPartner(
        name=name,
        website=website,
        commission_rate=commission_rate,
        certified=certified,
        security_endorsed=security_endorsed,
        active=True,
    )
    db.add(partner)
    db.flush()
    log_action(db, current.user.id, current.site_id, "add_travel_partner", "travel_agency_partner", partner.id, name)
    db.commit()
    db.refresh(partner)
    return {"id": partner.id, "name": partner.name, "certified": partner.certified}
