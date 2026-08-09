from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..models.operations import QueueSample
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS

router = APIRouter(prefix="/queues", tags=["queues"])

QUEUE_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS)


@router.get("")
def list_queues(
    site_id: int | None = None,
    limit: int = 20,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*QUEUE_ROLES))] = None,
):
    if site_id is None:
        site_id = current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    return [
        {
            "id": q.id,
            "queue_type": q.queue_type,
            "location": q.location,
            "current_length": q.current_length,
            "avg_wait_minutes": q.avg_wait_minutes,
            "open_counters": q.open_counters,
            "processing_rate": q.processing_rate,
            "recorded_at": q.recorded_at.isoformat(),
        }
        for q in db.scalars(select(QueueSample).where(QueueSample.site_id == site_id).order_by(QueueSample.recorded_at.desc()).limit(limit))
    ]


@router.post("")
def record_queue_sample(
    queue_type: str,
    location: str,
    current_length: int,
    avg_wait_minutes: float,
    open_counters: int = 1,
    processing_rate: float = 1.0,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*QUEUE_ROLES))] = None,
):
    sample = QueueSample(
        site_id=current.site_id,
        queue_type=queue_type,
        location=location,
        current_length=current_length,
        avg_wait_minutes=avg_wait_minutes,
        open_counters=open_counters,
        processing_rate=processing_rate,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(sample)
    db.flush()
    log_action(db, current.user.id, current.site_id, "record_queue_sample", "queue_sample", sample.id)
    db.commit()
    return {"id": sample.id, "queue_type": queue_type, "current_length": current_length}
