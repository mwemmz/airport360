from datetime import date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..attendance_service import roster_daily_summary
from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..hr_access import approver_department_id, employee_name
from ..models.core import Employee
from ..models.hr import Shift, ShiftAssignment
from ..schemas import ShiftAssignmentCreate, ShiftAssignmentOut, ShiftCreate, ShiftOut
from ..security import ROLE_ADMIN, ROLE_APPROVER, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_STAFF

router = APIRouter(prefix="/hr/roster", tags=["hr"])


def _load_assignment(db: Session, assignment_id: int) -> ShiftAssignment:
    assignment = db.get(ShiftAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Shift assignment not found")
    return assignment


def _parse_clock(value: str) -> time:
    hour, minute = (int(x) for x in value.split(":"))
    return time(hour, minute)


@router.get("/shifts", response_model=list[ShiftOut])
def list_shifts(
    department_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_EXECUTIVE, ROLE_STAFF))] = None,
):
    stmt = select(Shift).where(Shift.site_id == current.site_id, Shift.active.is_(True)).order_by(Shift.start_time)
    if department_id is not None:
        stmt = stmt.where(Shift.department_id == department_id)
    return db.scalars(stmt).all()


@router.post("/shifts", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
def create_shift(
    body: ShiftCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    if body.department_id is not None:
        from ..models.core import Department

        dept = db.get(Department, body.department_id)
        if not dept or dept.site_id != current.site_id:
            raise HTTPException(status_code=404, detail="Department not found")
    shift = Shift(
        site_id=current.site_id,
        department_id=body.department_id,
        name=body.name,
        start_time=_parse_clock(body.start_time),
        end_time=_parse_clock(body.end_time),
        shift_type=body.shift_type,
        standard_hours=body.standard_hours,
        min_staff=body.min_staff,
        description=body.description,
    )
    db.add(shift)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_shift", "shift", shift.id, shift.name, request)
    db.commit()
    db.refresh(shift)
    return shift


@router.get("/assignments", response_model=list[ShiftAssignmentOut])
def list_assignments(
    start: date,
    end: date,
    department_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_EXECUTIVE))] = None,
):
    stmt = (
        select(ShiftAssignment, Shift)
        .join(Shift, Shift.id == ShiftAssignment.shift_id)
        .where(ShiftAssignment.site_id == current.site_id, ShiftAssignment.work_date >= start, ShiftAssignment.work_date <= end)
        .order_by(ShiftAssignment.work_date, ShiftAssignment.employee_id)
    )
    if department_id is not None:
        stmt = stmt.where(Shift.department_id == department_id)
    if current.role == ROLE_APPROVER:
        dept = approver_department_id(db, current)
        if dept is None:
            return []
        stmt = stmt.where(Shift.department_id == dept)
    rows = db.execute(stmt).all()
    return [assignment for assignment, _ in rows]


@router.post("/assignments", response_model=ShiftAssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    body: ShiftAssignmentCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    emp = db.get(Employee, body.employee_id)
    if not emp or emp.site_id != current.site_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    shift = db.get(Shift, body.shift_id)
    if not shift or shift.site_id != current.site_id:
        raise HTTPException(status_code=404, detail="Shift not found")
    existing = db.scalar(
        select(ShiftAssignment.id).where(
            ShiftAssignment.employee_id == body.employee_id, ShiftAssignment.work_date == body.work_date
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Employee already has an assignment on this date")
    assignment = ShiftAssignment(
        site_id=current.site_id,
        employee_id=body.employee_id,
        shift_id=body.shift_id,
        work_date=body.work_date,
        note=body.note,
        created_by=current.user.id,
    )
    db.add(assignment)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_shift_assignment", "shift_assignment", assignment.id, f"{emp.employee_number} {body.work_date}", request)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/swap", response_model=ShiftAssignmentOut)
def swap_assignment(
    assignment_id: int,
    replacement_employee_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER))] = None,
):
    assignment = _load_assignment(db, assignment_id)
    if assignment.site_id != current.site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    replacement = db.get(Employee, replacement_employee_id)
    if not replacement or replacement.site_id != current.site_id:
        raise HTTPException(status_code=404, detail="Replacement employee not found")
    if current.role == ROLE_APPROVER:
        original = db.get(Employee, assignment.employee_id)
        dept = approver_department_id(db, current)
        if dept is None or original is None or original.department_id != dept or replacement.department_id != dept:
            raise HTTPException(status_code=403, detail="Department Head can only swap shifts within their own department")
    busy = db.scalar(
        select(ShiftAssignment.id).where(
            ShiftAssignment.employee_id == replacement_employee_id, ShiftAssignment.work_date == assignment.work_date
        )
    )
    if busy:
        raise HTTPException(status_code=409, detail="Replacement employee is already assigned on this date")
    assignment.status = "Swapped"
    assignment.swapped_with_employee_id = replacement_employee_id
    db.flush()
    swap_row = ShiftAssignment(
        site_id=current.site_id,
        employee_id=replacement_employee_id,
        shift_id=assignment.shift_id,
        work_date=assignment.work_date,
        status="Assigned",
        note=f"Swap for {employee_name(db, assignment.employee_id)}",
        created_by=current.user.id,
    )
    db.add(swap_row)
    db.flush()
    log_action(db, current.user.id, current.site_id, "swap_shift_assignment", "shift_assignment", assignment.id, f"-> {replacement_employee_id}", request)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/cancel", response_model=ShiftAssignmentOut)
def cancel_assignment(
    assignment_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    assignment = _load_assignment(db, assignment_id)
    if assignment.site_id != current.site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    assignment.status = "Cancelled"
    log_action(db, current.user.id, current.site_id, "cancel_shift_assignment", "shift_assignment", assignment.id, f"{assignment.work_date}", request)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("")
def roster_view(
    start: date,
    end: date,
    department_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_EXECUTIVE))] = None,
):
    """Daily roster calendar with understaffed flags and cost flags."""
    assert_site_access(current, current.site_id)
    if (end - start).days > 62:
        raise HTTPException(status_code=400, detail="Roster range too large (max 62 days)")
    days = roster_daily_summary(db, current.site_id, start, end, department_id)
    return {
        "site_id": current.site_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "department_id": department_id,
        "days": days,
    }


@router.get("/cost")
def roster_cost(
    start: date,
    end: date,
    department_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_APPROVER))] = None,
):
    """Roster-driven cost estimate: night-differential and overtime exposure."""
    days = roster_daily_summary(db, current.site_id, start, end, department_id)
    total_ot = round(sum(d["overtime_hours"] for d in days), 2)
    total_night = round(sum(d["night_hours"] for d in days), 2)
    return {
        "site_id": current.site_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "understaffed_days": sum(1 for d in days if d["understaffed_any"]),
        "total_overtime_hours": total_ot,
        "total_night_hours": total_night,
        "public_holiday_days": sum(1 for d in days if d["is_holiday"]),
        "label": "Simulated roster cost estimate",
    }
