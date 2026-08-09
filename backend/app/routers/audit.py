from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from ..deps import CurrentUser, DbSession, require_roles
from ..models.core import AuditLog
from ..schemas import AuditLogOut
from ..security import ROLE_ADMIN

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    entity_type: str | None = None,
    limit: int = 200,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN))] = None,
):
    stmt = select(AuditLog)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
    return db.scalars(stmt).all()
