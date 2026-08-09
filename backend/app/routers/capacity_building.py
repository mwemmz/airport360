from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..models.core import CapacityBuildingActivity, Site
from ..schemas import CapacityActivityCreate, CapacityActivityOut
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_HR

router = APIRouter(prefix="/capacity-building", tags=["capacity-building"])


@router.get("", response_model=list[CapacityActivityOut])
def list_activities(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_HR))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    return db.scalars(
        select(CapacityBuildingActivity)
        .where(CapacityBuildingActivity.site_id == site_id)
        .order_by(CapacityBuildingActivity.start_date.desc())
    ).all()


@router.post("", response_model=CapacityActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(
    body: CapacityActivityCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    activity = CapacityBuildingActivity(
        site_id=current.site_id,
        activity_type=body.activity_type,
        title=body.title,
        participant_category=body.participant_category,
        participants_count=body.participants_count,
        module_area=body.module_area,
        status=body.status,
        start_date=body.start_date,
        end_date=body.end_date,
        notes=body.notes,
    )
    db.add(activity)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_capacity_activity", "capacity_building_activity", activity.id, body.title, request)
    db.commit()
    db.refresh(activity)
    return activity
