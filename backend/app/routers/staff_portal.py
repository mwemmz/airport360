"""Frontline-staff portal surface.

A deliberately narrow read/write API for shared-terminal use by bottom-level
shift staff (security, ground, baggage, cleaning). Only the Frontline Staff
role may call these endpoints, and every mutation is scoped to the caller's own
employee record. Reuses the attendance / leave / case engines — no parallel data
model.
"""
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..attendance_service import staff_portal_clock
from ..audit import log_action
from ..deps import CurrentUser, DbSession, require_roles
from ..hr_cases import create_case
from ..leave_service import create_leave_request, list_balances
from ..models.core import Employee
from ..models.hr import HrCase, LeaveType, Shift, ShiftAssignment, TimeLog
from ..schemas import HrCaseCreate, LeaveRequestCreate, LeaveTypeOut, StaffPortalClockIn, TimeLogOut
from ..security import ROLE_FRONTLINE

router = APIRouter(prefix="/staff-portal", tags=["staff-portal"])


def _current_employee(db: Session, current: CurrentUser) -> Employee:
    if not current.user.employee_id:
        raise HTTPException(status_code=404, detail="No linked employee record")
    emp = db.get(Employee, current.user.employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.get("/home")
def staff_portal_home(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_FRONTLINE))] = None,
):
    emp = _current_employee(db, current)
    today = date.today()
    log = db.scalar(select(TimeLog).where(TimeLog.employee_id == emp.id, TimeLog.work_date == today))
    cases = db.scalars(
        select(HrCase).where(HrCase.employee_id == emp.id, HrCase.status.notin_(["Resolved", "Closed"]))
    ).all()
    upcoming = db.scalars(
        select(ShiftAssignment).where(
            ShiftAssignment.employee_id == emp.id,
            ShiftAssignment.work_date >= today,
            ShiftAssignment.status != "Cancelled",
        )
    ).all()
    balances = list_balances(db, emp.site_id, employee_id=emp.id)
    return {
        "employee": {
            "id": emp.id,
            "employee_number": emp.employee_number,
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "job_title": emp.job_title,
        },
        "today": {
            "date": today.isoformat(),
            "clock_in": log.clock_in.isoformat() if log else None,
            "clock_out": log.clock_out.isoformat() if log and log.clock_out else None,
            "clocked_in": bool(log and log.clock_out is None),
        },
        "upcoming_shifts": len(upcoming),
        "next_shift": (upcoming[0].work_date.isoformat() if upcoming else None),
        "open_cases": len(cases),
        "balance": balances,
    }


@router.post("/clock", response_model=TimeLogOut, status_code=status.HTTP_200_OK)
def staff_portal_clock_endpoint(
    body: StaffPortalClockIn,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_FRONTLINE))] = None,
):
    emp = _current_employee(db, current)
    log = staff_portal_clock(db, emp.id, emp.site_id, body.action)
    log_action(db, current.user.id, current.site_id, "staff_portal_clock", "time_log", log.id, f"employee={emp.id} action={body.action}", request)
    db.commit()
    db.refresh(log)
    return log


@router.get("/shifts")
def staff_portal_shifts(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_FRONTLINE))] = None,
):
    emp = _current_employee(db, current)
    rows = db.execute(
        select(ShiftAssignment, Shift)
        .join(Shift, Shift.id == ShiftAssignment.shift_id)
        .where(
            ShiftAssignment.employee_id == emp.id,
            ShiftAssignment.work_date >= date.today(),
            ShiftAssignment.status != "Cancelled",
        )
        .order_by(ShiftAssignment.work_date)
    ).all()
    return [
        {
            "assignment_id": a.id,
            "work_date": a.work_date.isoformat(),
            "status": a.status,
            "shift": {
                "id": s.id,
                "name": s.name,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "is_night": s.is_night,
            },
        }
        for a, s in rows
    ]


@router.get("/leave-types", response_model=list[LeaveTypeOut])
def staff_portal_leave_types(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_FRONTLINE))] = None,
):
    emp = _current_employee(db, current)
    return [
        t for t in db.scalars(select(LeaveType).where(LeaveType.active.is_(True))).all()
        if emp.contract_type in t.applicable_contracts
    ]


@router.post("/leave", status_code=status.HTTP_201_CREATED)
def staff_portal_request_leave(
    body: LeaveRequestCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_FRONTLINE))] = None,
):
    emp = _current_employee(db, current)
    if body.employee_id != emp.id:
        raise HTTPException(status_code=403, detail="Portal leave requests are limited to your own record")
    req = create_leave_request(
        db, current, emp.id, body.leave_type_id, body.start_date, body.end_date, body.reason, current.user.id
    )
    log_action(db, current.user.id, current.site_id, "staff_portal_request_leave", "leave_request", req.id, req.request_number, request)
    db.commit()
    db.refresh(req)
    return {"id": req.id, "request_number": req.request_number, "status": req.status}


@router.get("/balance")
def staff_portal_balance(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_FRONTLINE))] = None,
):
    emp = _current_employee(db, current)
    return list_balances(db, emp.site_id, employee_id=emp.id)


@router.get("/cases")
def staff_portal_cases(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_FRONTLINE))] = None,
):
    emp = _current_employee(db, current)
    cases = db.scalars(
        select(HrCase).where(HrCase.employee_id == emp.id).order_by(HrCase.opened_at.desc())
    ).all()
    return [
        {
            "id": c.id,
            "case_number": c.case_number,
            "category": c.category,
            "severity": c.severity,
            "status": c.status,
            "title": c.title,
            "opened_at": c.opened_at.isoformat(),
        }
        for c in cases
    ]


@router.post("/case", status_code=status.HTTP_201_CREATED)
def staff_portal_open_case(
    body: HrCaseCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_FRONTLINE))] = None,
):
    emp = _current_employee(db, current)
    if body.employee_id != emp.id:
        raise HTTPException(status_code=403, detail="Portal cases are limited to your own record")
    case = create_case(db, current, emp.site_id, emp.id, body.category, body.title, body.description, body.severity)
    log_action(db, current.user.id, current.site_id, "staff_portal_open_case", "hr_case", case.id, case.case_number, request)
    db.commit()
    return {"id": case.id, "case_number": case.case_number, "status": case.status}
