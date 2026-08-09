from fastapi import Request
from sqlalchemy.orm import Session

from .models.core import AuditLog


def log_action(
    db: Session,
    user_id: int,
    site_id: int,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    detail: str | None = None,
    request: Request | None = None,
) -> None:
    """Write an audit entry for every write operation. No writes should bypass this."""
    entry = AuditLog(
        user_id=user_id,
        site_id=site_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(entry)
