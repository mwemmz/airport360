from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models.core import Site, User
from .security import ROLE_ADMIN, ROLE_EXECUTIVE, decode_access_token

DbSession = Annotated[Session, Depends(get_db)]


class CurrentUser:
    def __init__(self, user: User, site: Site):
        self.user = user
        self.site = site

    @property
    def role(self) -> str:
        return self.user.role.name

    @property
    def site_id(self) -> int:
        return self.user.site_id


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return authorization.split(" ", 1)[1]


def get_current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    token = _extract_token(authorization)
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = int(payload.get("sub", "0"))
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    site = db.get(Site, user.site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User site not found")

    return CurrentUser(user=user, site=site)


def require_roles(*roles: str):
    """RBAC guard enforced at the API layer — every endpoint independently rejects out-of-role callers."""

    def dependency(current: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if current.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{current.role}' is not allowed")
        return current

    return dependency


def is_admin(current: CurrentUser) -> bool:
    return current.role == ROLE_ADMIN


def assert_site_access(current: CurrentUser, site_id: int) -> None:
    """Site isolation — an authenticated request must resolve to exactly its own site
    unless the caller is an Administrator or an Executive (explicitly authorized cross-site set).
    Cross-site reads for Executive are read-only because every mutating endpoint requires a
    site-scoped role (HR Officer / Finance Officer / Department Head / Staff)."""
    if current.role in (ROLE_ADMIN, ROLE_EXECUTIVE):
        return
    if current.site_id != site_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-site access denied")
