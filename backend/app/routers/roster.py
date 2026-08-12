from datetime import date, datetime, time, timedelta
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
from ..schemas import (
    ConflictEmployeeOut,
    ShiftAssignmentCreate,
    ShiftAssignmentOut,
    ShiftAssignmentUpdate,
    ShiftAssignmentView,
    ShiftConflictOut,
    ShiftCreate,
    ShiftOut,
    ShiftUpdate,
)
from ..security import ROLE_ADMIN, ROLE_APPROVER, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_STAFF

router = APIRouter(prefix="/hr/roster", tags=["hr"])


def _load_assignment(db: Session, assignment_id: int) -> ShiftAssignment:
    assignment = db.get(ShiftAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Shift assignment not found")
    return assignment


def _load_shift(db: Session, shift_id: int) -> Shift:
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


def _check_department(db: Session, department_id: int | None, site_id: int) -> None:
    if department_id is None:
        return
    from ..models.core import Department

    dept = db.get(Department, department_id)
    if not dept or dept.site_id != site_id:
        raise HTTPException(status_code=404, detail="Department not found")


def _assert_free(db: Session, site_id: int, employee_id: int, work_date: date, exclude_id: int | None = None) -> None:
    stmt = select(ShiftAssignment.id).where(
        ShiftAssignment.site_id == site_id,
        ShiftAssignment.employee_id == employee_id,
        ShiftAssignment.work_date == work_date,
        ShiftAssignment.status != "Cancelled",
    )
    if exclude_id is not None:
        stmt = stmt.where(ShiftAssignment.id != exclude_id)
    if db.scalar(stmt):
        raise HTTPException(status_code=409, detail="Employee already has an assignment on this date")


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
    _check_department(db, body.department_id, current.site_id)
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


@router.put("/shifts/{shift_id}", response_model=ShiftOut)
def update_shift(
    shift_id: int,
    body: ShiftUpdate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    shift = _load_shift(db, shift_id)
    if shift.site_id != current.site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    if body.department_id is not None and body.department_id != shift.department_id:
        _check_department(db, body.department_id, current.site_id)
    changes = []
    if body.name is not None:
        shift.name = body.name
        changes.append("name")
    if body.start_time is not None:
        shift.start_time = _parse_clock(body.start_time)
        changes.append("start_time")
    if body.end_time is not None:
        shift.end_time = _parse_clock(body.end_time)
        changes.append("end_time")
    if body.shift_type is not None:
        shift.shift_type = body.shift_type
        changes.append("shift_type")
    if body.standard_hours is not None:
        shift.standard_hours = body.standard_hours
        changes.append("standard_hours")
    if body.min_staff is not None:
        shift.min_staff = body.min_staff
        changes.append("min_staff")
    if body.department_id is not None:
        shift.department_id = body.department_id
        changes.append("department_id")
    if body.description is not None:
        shift.description = body.description
        changes.append("description")
    if body.active is not None:
        shift.active = body.active
        changes.append("active")
    log_action(db, current.user.id, current.site_id, "update_shift", "shift", shift.id, f"{shift.name} ({', '.join(changes)})", request)
    db.commit()
    db.refresh(shift)
    return shift


@router.delete("/shifts/{shift_id}", response_model=ShiftOut)
def deactivate_shift(
    shift_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    """Soft-delete: deactivates the shift so it leaves the pickers but its
    historical assignments remain intact."""
    shift = _load_shift(db, shift_id)
    if shift.site_id != current.site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    shift.active = False
    log_action(db, current.user.id, current.site_id, "deactivate_shift", "shift", shift.id, shift.name, request)
    db.commit()
    db.refresh(shift)
    return shift


@router.get("/assignments", response_model=list[ShiftAssignmentView])
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
    out = []
    for assignment, shift in rows:
        emp = db.get(Employee, assignment.employee_id)
        out.append(
            {
                "id": assignment.id,
                "employee_id": assignment.employee_id,
                "employee_number": emp.employee_number if emp else "",
                "employee_name": f"{emp.first_name} {emp.last_name}" if emp else f"#{assignment.employee_id}",
                "shift_id": shift.id,
                "shift_name": shift.name,
                "work_date": assignment.work_date,
                "status": assignment.status,
                "note": assignment.note,
            }
        )
    return out


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
    _assert_free(db, current.site_id, body.employee_id, body.work_date)
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


@router.put("/assignments/{assignment_id}", response_model=ShiftAssignmentOut)
def update_assignment(
    assignment_id: int,
    body: ShiftAssignmentUpdate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    """Reassign: change who works the shift, which shift, or the date. Reuses
    the same conflict rules as a fresh assignment (one person per day)."""
    assignment = _load_assignment(db, assignment_id)
    if assignment.site_id != current.site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    if body.employee_id is not None:
        emp = db.get(Employee, body.employee_id)
        if not emp or emp.site_id != current.site_id:
            raise HTTPException(status_code=404, detail="Employee not found")
        new_employee_id = body.employee_id
    else:
        new_employee_id = assignment.employee_id
    if body.shift_id is not None:
        shift = db.get(Shift, body.shift_id)
        if not shift or shift.site_id != current.site_id:
            raise HTTPException(status_code=404, detail="Shift not found")
        new_shift_id = body.shift_id
    else:
        new_shift_id = assignment.shift_id
    new_date = body.work_date if body.work_date is not None else assignment.work_date
    _assert_free(db, current.site_id, new_employee_id, new_date, exclude_id=assignment.id)
    assignment.employee_id = new_employee_id
    assignment.shift_id = new_shift_id
    assignment.work_date = new_date
    if body.note is not None:
        assignment.note = body.note
    log_action(db, current.user.id, current.site_id, "update_shift_assignment", "shift_assignment", assignment.id, f"{assignment.employee_id} {assignment.work_date}", request)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    """Unassign: permanently removes the assignment (unlike cancel, which keeps
    the history row with status=Cancelled)."""
    assignment = _load_assignment(db, assignment_id)
    if assignment.site_id != current.site_id:
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    log_action(db, current.user.id, current.site_id, "delete_shift_assignment", "shift_assignment", assignment.id, f"{assignment.work_date}", request)
    db.delete(assignment)
    db.commit()


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


@router.get("/conflicts", response_model=list[ShiftConflictOut])
def roster_conflicts(
    start: date,
    end: date,
    department_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_EXECUTIVE))] = None,
):
    """Roster conflict scan: every day where a shift is understaffed, plus the
    employees who could be assigned on that date to resolve it."""
    if (end - start).days > 62:
        raise HTTPException(status_code=400, detail="Roster range too large (max 62 days)")

    shift_stmt = select(Shift).where(
        Shift.site_id == current.site_id,
        Shift.active.is_(True),
    )
    if department_id is not None:
        shift_stmt = shift_stmt.where(Shift.department_id == department_id)
    if current.role == ROLE_APPROVER:
        dept = approver_department_id(db, current)
        if dept is None:
            return []
        shift_stmt = shift_stmt.where(Shift.department_id == dept)
    shifts = list(db.scalars(shift_stmt).all())

    assignment_stmt = (
        select(ShiftAssignment, Shift)
        .join(Shift, Shift.id == ShiftAssignment.shift_id)
        .where(
            ShiftAssignment.site_id == current.site_id,
            ShiftAssignment.work_date >= start,
            ShiftAssignment.work_date <= end,
            ShiftAssignment.status != "Cancelled",
        )
    )
    if department_id is not None:
        assignment_stmt = assignment_stmt.where(Shift.department_id == department_id)
    if current.role == ROLE_APPROVER:
        dept = approver_department_id(db, current)
        if dept is not None:
            assignment_stmt = assignment_stmt.where(Shift.department_id == dept)
    rows = db.execute(assignment_stmt).all()

    assigned_by: dict[tuple[date, int], int] = {}
    assigned_employees_by_day: dict[date, set[int]] = {}
    for assignment, shift in rows:
        key = (assignment.work_date, shift.id)
        assigned_by[key] = assigned_by.get(key, 0) + 1
        assigned_employees_by_day.setdefault(assignment.work_date, set()).add(assignment.employee_id)

    employees = list(
        db.scalars(
            select(Employee).where(
                Employee.site_id == current.site_id,
                Employee.employment_status == "Active",
            )
        ).all()
    )
    employees_by_dept: dict[int | None, list[Employee]] = {}
    for emp in employees:
        employees_by_dept.setdefault(emp.department_id, []).append(emp)

    conflicts: list[dict] = []
    day = start
    while day <= end:
        for shift in shifts:
            assigned = assigned_by.get((day, shift.id), 0)
            if assigned >= shift.min_staff:
                continue
            if shift.department_id is not None:
                pool = employees_by_dept.get(shift.department_id, [])
            else:
                pool = employees
            busy = assigned_employees_by_day.get(day, set())
            eligible = [
                emp
                for emp in pool
                if emp.id not in busy
            ][:10]
            conflicts.append(
                {
                    "date": day,
                    "shift_id": shift.id,
                    "shift_name": shift.name,
                    "shift_type": shift.shift_type,
                    "is_night": shift.is_night,
                    "min_staff": shift.min_staff,
                    "assigned": assigned,
                    "shortage": shift.min_staff - assigned,
                    "eligible_employees": [
                        {
                            "id": emp.id,
                            "employee_number": emp.employee_number,
                            "full_name": f"{emp.first_name} {emp.last_name}",
                            "job_title": emp.job_title,
                            "department_id": emp.department_id,
                        }
                        for emp in eligible
                    ],
                }
            )
        day += timedelta(days=1)
    return conflicts


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
