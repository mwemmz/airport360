from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..attendance_service import (
    create_time_log,
    list_time_logs,
    public_holidays_in_range,
    roster_daily_summary,
    weekly_overtime,
)
from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..hr_access import approver_department_id, employee_name
from ..models.core import Employee
from ..models.hr import PublicHoliday, TimeLog
from ..schemas import TimeLogCreate, TimeLogOut
from ..security import ROLE_ADMIN, ROLE_APPROVER, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_STAFF

router = APIRouter(prefix="/hr/attendance", tags=["hr"])


def _department_employee_ids(db: Session, current: CurrentUser) -> set[int]:
    dept = approver_department_id(db, current)
    if dept is None:
        return set()
    return set(db.scalars(select(Employee.id).where(Employee.department_id == dept)).all())


@router.get("/logs", response_model=list[TimeLogOut])
def get_logs(
    employee_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None,
):
    if current.role == ROLE_STAFF:
        if not current.user.employee_id:
            raise HTTPException(status_code=404, detail="No linked employee record")
        employee_id = current.user.employee_id
    elif current.role == ROLE_APPROVER:
        allowed = _department_employee_ids(db, current)
        rows = [t for t in list_time_logs(db, current.site_id, employee_id, start, end) if t.employee_id in allowed]
        return rows
    return list_time_logs(db, current.site_id, employee_id, start, end)


@router.post("/logs", response_model=TimeLogOut, status_code=status.HTTP_201_CREATED)
def add_time_log(
    body: TimeLogCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    log = create_time_log(db, current.user.id, current.site_id, body.employee_id, body.work_date, body.clock_in, body.clock_out, body.shift_id, body.notes)
    log_action(db, current.user.id, current.site_id, "create_time_log", "time_log", log.id, f"employee={log.employee_id} date={log.work_date}", request)
    db.commit()
    db.refresh(log)
    return log


@router.get("/weekly-overview")
def weekly_overview(
    start: date,
    end: date,
    employee_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER))] = None,
):
    rows, totals = weekly_overtime(db, current.site_id, start, end, employee_id)
    if current.role == ROLE_APPROVER:
        allowed = _department_employee_ids(db, current)
        rows = [r for r in rows if r["employee_id"] in allowed]
    decorated = [{**r, "employee_name": employee_name(db, r["employee_id"])} for r in rows]
    return {
        "site_id": current.site_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "weekly_standard_hours": 48.0,
        "weeks": decorated,
        "overtime_totals": {str(k): v for k, v in totals.items()},
    }


@router.get("/summary")
def attendance_summary(
    start: date,
    end: date,
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_HR, ROLE_FINANCE, ROLE_APPROVER))] = None,
):
    """Aggregate attendance analytics (Executive/BI read path)."""
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    logs = db.scalars(
        select(TimeLog).where(TimeLog.site_id == site_id, TimeLog.work_date >= start, TimeLog.work_date <= end)
    ).all()
    _, ot_totals = weekly_overtime(db, site_id, start, end)
    return {
        "site_id": site_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "employees_logged": len({log.employee_id for log in logs}),
        "total_hours": round(sum(log.hours_worked for log in logs), 2),
        "total_overtime_hours": round(sum(ot_totals.values()), 2),
        "total_night_hours": round(sum(log.night_hours for log in logs), 2),
        "public_holiday_hours": round(sum(log.hours_worked for log in logs if log.public_holiday), 2),
        "label": "Simulated attendance data",
    }


@router.get("/holidays")
def list_holidays(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None,
):
    return [
        {
            "id": h.id,
            "name": h.name,
            "holiday_date": h.holiday_date,
            "site_id": h.site_id,
        }
        for h in db.scalars(select(PublicHoliday).order_by(PublicHoliday.holiday_date)).all()
    ]


@router.post("/holidays", status_code=status.HTTP_201_CREATED)
def add_holiday(
    name: str,
    holiday_date: date,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    existing = db.scalar(select(PublicHoliday.id).where(PublicHoliday.holiday_date == holiday_date, PublicHoliday.site_id.is_(None)))
    if existing:
        raise HTTPException(status_code=409, detail=f"Public holiday already exists on {holiday_date}")
    holiday = PublicHoliday(name=name, holiday_date=holiday_date, site_id=None)
    db.add(holiday)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_public_holiday", "public_holiday", holiday.id, holiday.name, request)
    db.commit()
    db.refresh(holiday)
    return {"id": holiday.id, "name": holiday.name, "holiday_date": holiday.holiday_date}
