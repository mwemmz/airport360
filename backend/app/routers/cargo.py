from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from ..deps import CurrentUser, DbSession, require_roles
from ..models.operations import CargoShipment
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS, ROLE_STAFF

router = APIRouter(prefix="/cargo", tags=["cargo"])

CARGO_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS, ROLE_STAFF)


@router.get("")
def list_shipments(
    site_id: int | None = None,
    delayed_only: bool = False,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*CARGO_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        return []
    stmt = select(CargoShipment).where(CargoShipment.site_id == site_id)
    if delayed_only:
        stmt = stmt.where(CargoShipment.delayed.is_(True))
    return [
        {
            "id": c.id,
            "awb_number": c.awb_number,
            "origin": c.origin,
            "destination": c.destination,
            "status": c.status,
            "weight_kg": c.weight_kg,
            "storage_location": c.storage_location,
            "delayed": c.delayed,
            "registered_at": c.registered_at.isoformat(),
            "released_at": c.released_at.isoformat() if c.released_at else None,
        }
        for c in db.scalars(stmt.order_by(CargoShipment.registered_at.desc()).limit(50))
    ]
