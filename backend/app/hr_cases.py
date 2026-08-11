"""HR case management service.

Status flow: Logged -> Under Review -> Investigating -> Resolved -> Closed.
Access model (enforced on every read/write):
  - Administrator / HR Officer (same site): full manage + all notes.
  - Department Head: read access to cases for employees in their department
    (they manage leave and shift swaps for their own department, not HR cases).
  - Staff: read-only on their own cases (the subject), plus may add notes.
  - Executive: aggregate analytics only (see the analytics endpoint), never case files.
Every mutating action is appended to the case's note trail (audit trail).
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .audit import log_action
from .deps import CurrentUser
from .models.core import Employee, User
from .models.hr import HR_CASE_STATUSES, HrCase, HrCaseNote
from .security import ROLE_ADMIN, ROLE_APPROVER, ROLE_EXECUTIVE, ROLE_HR

ALLOWED_TRANSITIONS = {
    "Logged": {"Under Review", "Investigating"},
    "Under Review": {"Investigating", "Resolved"},
    "Investigating": {"Resolved", "Under Review"},
    "Resolved": {"Closed", "Under Review"},
    "Closed": set(),
}


def _next_case_number(db: Session, year: int) -> str:
    count = db.scalar(select(func.count(HrCase.id))) or 0
    return f"HRC-{year}-{count + 1:04d}"


def _approver_department_id(db: Session, user: User) -> int | None:
    if not user.employee_id:
        return None
    emp = db.get(Employee, user.employee_id)
    return emp.department_id if emp else None


def can_view_case(db: Session, current: CurrentUser, case: HrCase) -> bool:
    if current.role in (ROLE_ADMIN, ROLE_HR) and current.site_id == case.site_id:
        return True
    if current.role == ROLE_APPROVER and current.site_id == case.site_id:
        dept = _approver_department_id(db, current.user)
        emp = db.get(Employee, case.employee_id)
        return dept is not None and emp is not None and emp.department_id == dept
    if current.role == "Staff":
        return current.user.employee_id == case.employee_id
    return False


def can_manage_case(current: CurrentUser, case: HrCase) -> bool:
    return current.role in (ROLE_ADMIN, ROLE_HR) and current.site_id == case.site_id


def create_case(
    db: Session,
    current: CurrentUser,
    site_id: int,
    employee_id: int,
    category: str,
    title: str,
    description: str | None,
    severity: str = "MEDIUM",
) -> HrCase:
    employee = db.get(Employee, employee_id)
    if not employee or employee.site_id != site_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    case = HrCase(
        case_number=_next_case_number(db, datetime.now().year),
        site_id=site_id,
        employee_id=employee_id,
        reporter_user_id=current.user.id,
        category=category,
        severity=severity,
        status="Logged",
        title=title,
        description=description,
        assigned_user_id=current.user.id if current.role == ROLE_HR else None,
    )
    db.add(case)
    db.flush()
    note = HrCaseNote(
        case_id=case.id,
        user_id=current.user.id,
        note=f"Case logged by {current.user.full_name}: {title}",
        is_private=current.role == ROLE_HR,
    )
    db.add(note)
    db.flush()
    return case


def add_note(db: Session, current: CurrentUser, case: HrCase, note_text: str, is_private: bool = False) -> HrCaseNote:
    if not can_view_case(db, current, case):
        raise HTTPException(status_code=403, detail="You do not have access to this case")
    if is_private and not can_manage_case(current, case):
        raise HTTPException(status_code=403, detail="Only HR/Administrator can add private notes")
    note = HrCaseNote(case_id=case.id, user_id=current.user.id, note=note_text, is_private=is_private)
    db.add(note)
    db.flush()
    return note


def transition(db: Session, current: CurrentUser, case: HrCase, new_status: str, resolution_notes: str | None = None) -> HrCase:
    if not can_manage_case(current, case):
        raise HTTPException(status_code=403, detail="Only HR Officer or Administrator can update case status")
    if new_status not in HR_CASE_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unknown status '{new_status}'")
    if new_status == case.status:
        raise HTTPException(status_code=409, detail=f"Case is already '{new_status}'")
    if new_status not in ALLOWED_TRANSITIONS.get(case.status, set()):
        raise HTTPException(
            status_code=409, detail=f"Invalid transition {case.status} -> {new_status}"
        )
    case.status = new_status
    if new_status == "Resolved":
        case.resolution_notes = resolution_notes
        case.resolved_at = datetime.now()
    if new_status == "Closed":
        case.closed_at = datetime.now()
    note = HrCaseNote(
        case_id=case.id,
        user_id=current.user.id,
        note=f"Status -> {new_status}" + (f": {resolution_notes}" if resolution_notes else ""),
        is_private=True,
    )
    db.add(note)
    db.flush()
    return case


def assign_case(db: Session, current: CurrentUser, case: HrCase, assignee_user_id: int) -> HrCase:
    if not can_manage_case(current, case):
        raise HTTPException(status_code=403, detail="Only HR Officer or Administrator can assign cases")
    assignee = db.get(User, assignee_user_id)
    if not assignee or assignee.site_id != case.site_id:
        raise HTTPException(status_code=404, detail="Assignee not found")
    case.assigned_user_id = assignee.id
    note = HrCaseNote(
        case_id=case.id,
        user_id=current.user.id,
        note=f"Assigned to {assignee.full_name}",
        is_private=True,
    )
    db.add(note)
    db.flush()
    return case


def scoped_case_query(db: Session, current: CurrentUser, site_id: int):
    stmt = select(HrCase).where(HrCase.site_id == site_id)
    if current.role in (ROLE_ADMIN, ROLE_HR):
        return stmt
    if current.role == ROLE_APPROVER:
        dept = _approver_department_id(db, current.user)
        if dept is None:
            return stmt.where(0 == 1)
        return stmt.where(
            HrCase.employee_id.in_(select(Employee.id).where(Employee.department_id == dept))
        )
    if current.role == "Staff":
        return stmt.where(HrCase.employee_id == current.user.employee_id)
    return stmt.where(0 == 1)


def list_visible_notes(db: Session, current: CurrentUser, case: HrCase) -> list[HrCaseNote]:
    if not can_view_case(db, current, case):
        raise HTTPException(status_code=403, detail="You do not have access to this case")
    stmt = select(HrCaseNote).where(HrCaseNote.case_id == case.id).order_by(HrCaseNote.created_at)
    if not can_manage_case(current, case):
        stmt = stmt.where(HrCaseNote.is_private.is_(False))
    return list(db.scalars(stmt).all())


def case_analytics(db: Session, current: CurrentUser, site_id: int) -> dict:
    """Aggregate analytics — the only case data visible to Executive/BI."""
    base = select(HrCase).where(HrCase.site_id == site_id)
    if not (current.role in (ROLE_ADMIN, ROLE_HR, ROLE_EXECUTIVE) or current.site_id == site_id):
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    cases = list(db.scalars(base).all())
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for case in cases:
        by_status[case.status] = by_status.get(case.status, 0) + 1
        by_category[case.category] = by_category.get(case.category, 0) + 1
    return {
        "site_id": site_id,
        "total": len(cases),
        "open": sum(v for k, v in by_status.items() if k in ("Logged", "Under Review", "Investigating")),
        "resolved": by_status.get("Resolved", 0),
        "closed": by_status.get("Closed", 0),
        "by_status": by_status,
        "by_category": by_category,
        "label": "Simulated case data",
    }
