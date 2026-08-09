from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..models.core import Site
from ..schemas import SiteCreate, SiteOut
from ..security import ROLE_ADMIN

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=list[SiteOut])
def list_sites(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN))] = None,
):
    return db.scalars(select(Site).order_by(Site.id)).all()


@router.post("", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
def create_site(
    body: SiteCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN))] = None,
):
    dup = db.scalar(select(Site).where(Site.code == body.code.upper()))
    if dup:
        raise HTTPException(status_code=409, detail="Site code already exists")
    site = Site(code=body.code.upper(), name=body.name, city=body.city, country=body.country, iata_code=body.iata_code)
    db.add(site)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_site", "site", site.id, body.name, request)
    db.commit()
    db.refresh(site)
    return site
