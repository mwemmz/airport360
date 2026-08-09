from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..deps import CurrentUser, DbSession, require_roles
from ..ml.assistant import answer_question, generate_recommendations
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS

router = APIRouter(prefix="/ai", tags=["ai"])

AI_ROLES = (ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_OPS)


def _resolve_site(current: CurrentUser, site_id: int | None) -> int:
    if site_id is None:
        return current.site_id
    if current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE) and current.site_id != site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    return site_id


@router.get("/recommendations")
def recommendations(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*AI_ROLES))] = None,
):
    sid = _resolve_site(current, site_id)
    return generate_recommendations(db, sid)


@router.get("/answer")
def answer(
    question: str,
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(*AI_ROLES))] = None,
):
    sid = _resolve_site(current, site_id)
    return answer_question(db, sid, question).to_dict()
