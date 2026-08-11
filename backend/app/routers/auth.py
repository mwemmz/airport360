from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..audit import log_action
from ..deps import CurrentUser, DbSession, get_current_user
from ..models.core import Employee, User
from ..schemas import KioskLoginIn, LoginIn, TokenOut, UserOut
from ..security import (
    ROLE_FRONTLINE,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: DbSession, request: Request):
    user = db.scalar(
        select(User).options(selectinload(User.role)).where(User.email == body.email.lower())
    )
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(user.id, user.site_id, user.role.name)
    log_action(db, user.id, user.site_id, "login", "user", user.id, "User logged in", request)
    db.commit()
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/kiosk", response_model=TokenOut)
def kiosk_login(body: KioskLoginIn, db: DbSession, request: Request):
    """Shared-terminal login for Frontline Staff: employee number + numeric PIN."""
    emp = db.scalar(select(Employee).where(Employee.employee_number == body.employee_number.strip()))
    if not emp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid employee number or PIN")
    user = db.scalar(
        select(User).options(selectinload(User.role)).where(User.employee_id == emp.id)
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid employee number or PIN")
    if user.role.name != ROLE_FRONTLINE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kiosk login is only available to Frontline Staff")
    if not user.pin_hash or not verify_password(body.pin.strip(), user.pin_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid employee number or PIN")
    if not user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(user.id, user.site_id, user.role.name)
    log_action(db, user.id, user.site_id, "kiosk_login", "user", user.id, f"kiosk {body.employee_number}", request)
    db.commit()
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current: Annotated[CurrentUser, Depends(get_current_user)] = None, db: DbSession = None):
    user = db.scalar(
        select(User).options(selectinload(User.role)).where(User.id == current.user.id)
    )
    return user
