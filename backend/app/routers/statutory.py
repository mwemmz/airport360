from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..models.hr import StatutoryConfig
from ..schemas import StatutoryConfigOut, StatutoryConfigUpdate
from ..security import ROLE_ADMIN, ROLE_HR
from ..statutory_config import get_effective_rates, seed_statutory_config, statutory_sources, upsert_config

router = APIRouter(prefix="/hr/statutory-config", tags=["hr"])


@router.get("", response_model=list[StatutoryConfigOut])
def list_config(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    """All config versions (history retained)."""
    seed_statutory_config(db)
    return db.scalars(select(StatutoryConfig).order_by(StatutoryConfig.config_key, StatutoryConfig.effective_date)).all()


@router.get("/effective")
def effective_config(
    as_of: date | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    """Rates in force (optionally as of a historical date), with source labels."""
    seed_statutory_config(db)
    return get_effective_rates(db, as_of)


@router.get("/sources")
def config_sources(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    """Source + effective-date labels for every statutory rate."""
    seed_statutory_config(db)
    return statutory_sources(db)


@router.post("/seed", status_code=status.HTTP_201_CREATED)
def seed_config(
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN))] = None,
):
    inserted = seed_statutory_config(db)
    log_action(db, current.user.id, current.site_id, "seed_statutory_config", "statutory_config", None, f"{inserted} rows", request)
    db.commit()
    return {"inserted": inserted}


@router.put("/{config_key}", response_model=StatutoryConfigOut)
def update_config(
    config_key: str,
    body: StatutoryConfigUpdate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN))] = None,
):
    """Insert a new effective version (existing versions stay for history)."""
    known = set(get_effective_rates(db).keys())
    if config_key not in known:
        raise HTTPException(status_code=404, detail=f"Unknown config key '{config_key}'")
    effective = body.effective_date or date.today()
    row = upsert_config(db, config_key, body.value, body.source, effective)
    log_action(db, current.user.id, current.site_id, "update_statutory_config", "statutory_config", row.id, f"{config_key} @ {effective}", request)
    db.commit()
    db.refresh(row)
    return row
