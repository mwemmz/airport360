from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..models.core import Role, Site, User
from ..schemas import SiteCreate, SiteOut, UserCreate, UserOut
from ..security import ROLE_ADMIN, ALL_ROLES, hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN))] = None,
):
    stmt = (
        select(User)
        .options(selectinload(User.role))
        .order_by(User.id)
    )
    if current.role == ROLE_ADMIN:
        return [UserOut.model_validate(u) for u in db.scalars(stmt)]
    return []


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: DbSession,
    request: Request,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN))] = None,
):
    if body.role not in ALL_ROLES:
        raise HTTPException(status_code=400, detail=f"Unknown role '{body.role}'")
    role = db.scalar(select(Role).where(Role.name == body.role))
    if not role:
        raise HTTPException(status_code=400, detail="Role not configured")
    site = db.get(Site, body.site_id)
    if not site:
        raise HTTPException(status_code=400, detail="Site not found")

    existing = db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email.lower(),
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role_id=role.id,
        site_id=site.id,
        employee_id=body.employee_id,
    )
    db.add(user)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_user", "user", user.id, body.email, request)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=UserOut)
def set_user_status(
    user_id: int,
    active: bool,
    db: DbSession,
    request: Request,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN))] = None,
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.active = active
    log_action(db, current.user.id, current.site_id, "toggle_user_active", "user", user.id, f"active={active}", request)
    db.commit()
    db.refresh(user)
    return user
