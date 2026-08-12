from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..hr_access import employee_name
from ..hr_cases import (
    add_note,
    assign_case,
    can_view_case,
    case_analytics,
    create_case,
    list_visible_notes,
    scoped_case_query,
    transition,
)
from ..models.core import Employee, Role, User
from ..models.hr import HrCase
from ..schemas import (
    HrCaseAssign,
    HrCaseCreate,
    HrCaseNoteCreate,
    HrCaseNoteOut,
    HrCaseOut,
    HrCaseTransition,
    UserOut,
)
from ..security import ROLE_ADMIN, ROLE_APPROVER, ROLE_EXECUTIVE, ROLE_HR, ROLE_STAFF

router = APIRouter(prefix="/hr/cases", tags=["hr"])


def _serialize(db: Session, case: HrCase) -> dict:
    data = {
        "id": case.id,
        "case_number": case.case_number,
        "site_id": case.site_id,
        "employee_id": case.employee_id,
        "employee_name": employee_name(db, case.employee_id),
        "reporter_user_id": case.reporter_user_id,
        "category": case.category,
        "severity": case.severity,
        "status": case.status,
        "title": case.title,
        "description": case.description,
        "assigned_user_id": case.assigned_user_id,
        "resolution_notes": case.resolution_notes,
        "opened_at": case.opened_at,
        "updated_at": case.updated_at,
        "resolved_at": case.resolved_at,
        "closed_at": case.closed_at,
    }
    return data


def _load_case(db: Session, case_id: int) -> HrCase:
    case = db.get(HrCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/analytics")
def cases_analytics(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_EXECUTIVE, ROLE_APPROVER))] = None,
):
    """Aggregate analytics — the only HR-case surface available to Executive/BI."""
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    return case_analytics(db, current, site_id)


@router.get("", response_model=list[HrCaseOut])
def list_cases(
    category: str | None = None,
    status_filter: str | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None,
):
    stmt = scoped_case_query(db, current, current.site_id).order_by(HrCase.opened_at.desc())
    if category:
        stmt = stmt.where(HrCase.category == category)
    if status_filter:
        stmt = stmt.where(HrCase.status == status_filter)
    cases = db.scalars(stmt).all()
    return [_serialize(db, c) for c in cases]


@router.get("/assignees", response_model=list[UserOut])
def case_assignees(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    """HR/Admin users at the current site who can be assigned a case."""
    stmt = (
        select(User)
        .join(Role, Role.id == User.role_id)
        .options(selectinload(User.role))
        .where(
            User.site_id == current.site_id,
            User.active.is_(True),
            Role.name.in_([ROLE_ADMIN, ROLE_HR]),
        )
        .order_by(User.full_name)
    )
    return [UserOut.model_validate(u) for u in db.scalars(stmt).all()]


@router.get("/{case_id}", response_model=HrCaseOut)
def get_case(
    case_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None,
):
    case = _load_case(db, case_id)
    if not can_view_case(db, current, case):
        raise HTTPException(status_code=403, detail="You do not have access to this case")
    return _serialize(db, case)


@router.post("", response_model=HrCaseOut, status_code=status.HTTP_201_CREATED)
def open_case(
    body: HrCaseCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_STAFF))] = None,
):
    if current.role == ROLE_STAFF:
        if not current.user.employee_id:
            raise HTTPException(status_code=404, detail="No linked employee record")
        body.employee_id = current.user.employee_id
    case = create_case(db, current, current.site_id, body.employee_id, body.category, body.title, body.description, body.severity)
    log_action(db, current.user.id, current.site_id, "create_hr_case", "hr_case", case.id, case.case_number, request)
    db.commit()
    db.refresh(case)
    return _serialize(db, case)


@router.get("/{case_id}/notes", response_model=list[HrCaseNoteOut])
def case_notes(
    case_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None,
):
    case = _load_case(db, case_id)
    return list_visible_notes(db, current, case)


@router.post("/{case_id}/notes", response_model=HrCaseNoteOut, status_code=status.HTTP_201_CREATED)
def add_case_note(
    case_id: int,
    body: HrCaseNoteCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None,
):
    case = _load_case(db, case_id)
    note = add_note(db, current, case, body.note, body.is_private)
    log_action(db, current.user.id, current.site_id, "add_hr_case_note", "hr_case", case.id, f"note #{note.id}", request)
    db.commit()
    db.refresh(note)
    return note


@router.post("/{case_id}/status", response_model=HrCaseOut)
def update_status(
    case_id: int,
    body: HrCaseTransition,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    case = _load_case(db, case_id)
    case = transition(db, current, case, body.status, body.resolution_notes)
    log_action(db, current.user.id, current.site_id, "transition_hr_case", "hr_case", case.id, f"{case.status}", request)
    db.commit()
    db.refresh(case)
    return _serialize(db, case)


@router.post("/{case_id}/assign", response_model=HrCaseOut)
def assign_case_endpoint(
    case_id: int,
    body: HrCaseAssign,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    case = _load_case(db, case_id)
    case = assign_case(db, current, case, body.assignee_user_id)
    log_action(db, current.user.id, current.site_id, "assign_hr_case", "hr_case", case.id, f"assignee={body.assignee_user_id}", request)
    db.commit()
    db.refresh(case)
    return _serialize(db, case)
