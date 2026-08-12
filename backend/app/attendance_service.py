"""Time & attendance computation layer.

Rules (all configurable via statutory_config):
- Night work window: 18:00-06:00, hours inside it carry a premium (payroll side).
- Daily standard hours: the assigned shift's standard_hours (default 8).
- Overtime: hours beyond the 48-hour weekly threshold (Employment Code Act 2019).
  Daily overtime (beyond the shift standard) is also recorded per day for display;
  the authoritative payroll OT figure is the weekly-threshold calculation.
- Public holiday and rest-day work is flagged for the higher multiplier.
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models.core import Employee
from .models.hr import PublicHoliday, Shift, TimeLog
from .statutory_config import get_effective_rates

WEEKLY_STANDARD_HOURS = 48.0


def _parse_time(value: str) -> time:
    hour, minute = (int(x) for x in value.split(":"))
    return time(hour, minute)


def night_hours(clock_in: datetime, clock_out: datetime, window_start: str = "18:00", window_end: str = "06:00") -> float:
    """Hours inside the night window for a clock_in/clock_out pair."""
    start_hour = _parse_time(window_start)
    end_hour = _parse_time(window_end)
    total = 0.0
    window_end_dt = datetime.combine(clock_in.date(), end_hour)
    # The window [start, end] may wrap past midnight; walk forward a day at a time.
    seg_start = datetime.combine(clock_in.date(), start_hour)
    if clock_in.time() >= start_hour:
        window_end_dt = window_end_dt + timedelta(days=1)
    cur = clock_in
    while cur < clock_out:
        lo = max(cur, seg_start)
        hi = min(clock_out, window_end_dt)
        if hi > lo:
            total += (hi - lo).total_seconds() / 3600
        if window_end_dt >= clock_out:
            break
        seg_start = datetime.combine((window_end_dt + timedelta(days=1)).date(), start_hour)
        window_end_dt = window_end_dt + timedelta(days=1)
        cur = window_end_dt - timedelta(days=0)
        cur = window_end_dt
    return round(total, 2)


def is_public_holiday(db: Session, site_id: int, day: date) -> bool:
    return db.scalar(
        select(PublicHoliday.id).where(
            PublicHoliday.holiday_date == day,
            (PublicHoliday.site_id.is_(None)) | (PublicHoliday.site_id == site_id),
        )
    ) is not None


def public_holidays_in_range(db: Session, site_id: int, start: date, end: date) -> set[date]:
    rows = db.scalars(
        select(PublicHoliday.holiday_date).where(
            PublicHoliday.holiday_date >= start,
            PublicHoliday.holiday_date <= end,
            (PublicHoliday.site_id.is_(None)) | (PublicHoliday.site_id == site_id),
        )
    ).all()
    return set(rows)


def create_time_log(
    db: Session,
    current_user_id: int,
    site_id: int,
    employee_id: int,
    work_date: date,
    clock_in: datetime,
    clock_out: datetime,
    shift_id: int | None = None,
    notes: str | None = None,
) -> TimeLog:
    employee = db.get(Employee, employee_id)
    if not employee or employee.site_id != site_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    if clock_out <= clock_in:
        raise HTTPException(status_code=400, detail="clock_out must be after clock_in")

    shift = db.get(Shift, shift_id) if shift_id else None
    if shift_id and (not shift or shift.site_id != site_id):
        raise HTTPException(status_code=404, detail="Shift not found")

    rates = get_effective_rates(db)
    standard_hours = (shift.standard_hours if shift else 8.0) or 8.0
    duration = round((clock_out - clock_in).total_seconds() / 3600, 2)
    night = night_hours(clock_in, clock_out, rates["night_work"]["window_start"], rates["night_work"]["window_end"])
    holiday = is_public_holiday(db, site_id, work_date)
    rest_day = work_date.weekday() >= 5

    log = TimeLog(
        site_id=site_id,
        employee_id=employee_id,
        work_date=work_date,
        clock_in=clock_in,
        clock_out=clock_out,
        hours_worked=duration,
        standard_hours=standard_hours,
        overtime_hours=max(0.0, round(duration - standard_hours, 2)),
        night_hours=night,
        public_holiday=holiday,
        is_rest_day=rest_day,
        source="manual",
        notes=notes,
    )
    db.add(log)
    db.flush()
    return log


def staff_portal_clock(db: Session, employee_id: int, site_id: int, action: str, now: datetime | None = None) -> TimeLog:
    """Frontline-staff portal clock: 'in' opens today's log, 'out' closes it and
    recomputes hours/night/overtime exactly as the manual-creation path does."""
    now = now or datetime.now()
    employee = db.get(Employee, employee_id)
    if not employee or employee.site_id != site_id:
        raise HTTPException(status_code=404, detail="Employee not found")

    from .models.hr import ShiftAssignment

    log = db.scalar(
        select(TimeLog).where(TimeLog.employee_id == employee_id, TimeLog.work_date == now.date())
    )
    shift = None
    assignment = db.scalar(
        select(ShiftAssignment).where(
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.work_date == now.date(),
            ShiftAssignment.status != "Cancelled",
        )
    )
    if assignment:
        shift = db.get(Shift, assignment.shift_id)

    rates = get_effective_rates(db)
    standard_hours = (shift.standard_hours if shift else 8.0) or 8.0

    if action == "in":
        if log and log.clock_out is None:
            raise HTTPException(status_code=400, detail="Already clocked in today")
        if log:
            raise HTTPException(status_code=409, detail="Already clocked out today")
        log = TimeLog(
            site_id=site_id,
            employee_id=employee_id,
            work_date=now.date(),
            clock_in=now,
            clock_out=None,
            hours_worked=0.0,
            standard_hours=standard_hours,
            overtime_hours=0.0,
            night_hours=0.0,
            public_holiday=is_public_holiday(db, site_id, now.date()),
            is_rest_day=now.weekday() >= 5,
            source="staff-portal",
        )
        db.add(log)
        db.flush()
        return log

    if action == "out":
        if not log or log.clock_out is not None:
            raise HTTPException(status_code=400, detail="No open time log to close")
        log.clock_out = now
        log.hours_worked = round((log.clock_out - log.clock_in).total_seconds() / 3600, 2)
        log.night_hours = night_hours(log.clock_in, log.clock_out, rates["night_work"]["window_start"], rates["night_work"]["window_end"])
        log.overtime_hours = max(0.0, round(log.hours_worked - log.standard_hours, 2))
        log.public_holiday = is_public_holiday(db, site_id, now.date())
        log.is_rest_day = now.weekday() >= 5
        db.flush()
        return log

    raise HTTPException(status_code=400, detail="action must be 'in' or 'out'")


def _weeks(start: date, end: date) -> Iterable[date]:
    """ISO week start dates (Monday) covering [start, end]."""
    week = start - timedelta(days=start.weekday())
    while week <= end:
        yield week
        week += timedelta(days=7)


def weekly_overtime(db: Session, site_id: int, start: date, end: date, employee_id: int | None = None) -> list[dict]:
    """Per employee per ISO week: total hours vs the 48-hour threshold.

    Overtime for the period = sum over weeks of max(0, week_hours - 48).
    Returns both the weekly rows (for the report) and per-employee period totals.
    """
    rows = db.scalars(
        select(TimeLog).where(
            TimeLog.site_id == site_id,
            TimeLog.work_date >= start,
            TimeLog.work_date <= end,
            TimeLog.clock_out.is_not(None),
        )
    ).all()
    if employee_id is not None:
        rows = [r for r in rows if r.employee_id == employee_id]

    by_week_emp: dict[tuple[date, int], float] = defaultdict(float)
    for log in rows:
        week = log.work_date - timedelta(days=log.work_date.weekday())
        by_week_emp[(week, log.employee_id)] += log.hours_worked

    week_rows = []
    for week in _weeks(start, end):
        for (w, emp_id), hours in sorted(by_week_emp.items()):
            if w != week:
                continue
            ot = max(0.0, round(hours - WEEKLY_STANDARD_HOURS, 2))
            week_rows.append(
                {
                    "week_start": w.isoformat(),
                    "employee_id": emp_id,
                    "hours_worked": round(hours, 2),
                    "weekly_standard_hours": WEEKLY_STANDARD_HOURS,
                    "overtime_hours": ot,
                    "threshold_exceeded": ot > 0,
                }
            )
    week_rows.sort(key=lambda r: (r["week_start"], r["employee_id"]))

    totals: dict[int, float] = defaultdict(float)
    for r in week_rows:
        totals[r["employee_id"]] += r["overtime_hours"]
    return week_rows, {k: round(v, 2) for k, v in totals.items()}


def overtime_hours_for_period(db: Session, site_id: int, start: date, end: date, employee_id: int) -> float:
    _, totals = weekly_overtime(db, site_id, start, end, employee_id=employee_id)
    return totals.get(employee_id, 0.0)


def list_time_logs(db: Session, site_id: int, employee_id: int | None = None, start: date | None = None, end: date | None = None) -> list[TimeLog]:
    stmt = select(TimeLog).where(TimeLog.site_id == site_id).order_by(TimeLog.work_date.desc(), TimeLog.id)
    if employee_id is not None:
        stmt = stmt.where(TimeLog.employee_id == employee_id)
    if start is not None:
        stmt = stmt.where(TimeLog.work_date >= start)
    if end is not None:
        stmt = stmt.where(TimeLog.work_date <= end)
    return list(db.scalars(stmt).all())


def roster_daily_summary(db: Session, site_id: int, start: date, end: date, department_id: int | None = None) -> list[dict]:
    """Per-day coverage for the roster view: assigned count vs shift minimum,
    plus night/OT cost flags driven by time logs in the same range."""
    from .models.hr import ShiftAssignment

    stmt = (
        select(ShiftAssignment, Shift)
        .join(Shift, Shift.id == ShiftAssignment.shift_id)
        .where(ShiftAssignment.site_id == site_id, ShiftAssignment.work_date >= start, ShiftAssignment.work_date <= end, ShiftAssignment.status != "Cancelled")
        .order_by(ShiftAssignment.work_date)
    )
    if department_id is not None:
        stmt = stmt.where(Shift.department_id == department_id)
    rows = db.execute(stmt).all()

    holiday_set = public_holidays_in_range(db, site_id, start, end)
    logs = db.scalars(
        select(TimeLog).where(TimeLog.site_id == site_id, TimeLog.work_date >= start, TimeLog.work_date <= end)
    ).all()
    logs_by_day: dict[date, list[TimeLog]] = defaultdict(list)
    for log in logs:
        logs_by_day[log.work_date].append(log)

    days: dict[date, dict] = {}
    for assignment, shift in rows:
        day = days.setdefault(
            assignment.work_date,
            {"date": assignment.work_date.isoformat(), "shifts": {}, "is_holiday": assignment.work_date in holiday_set},
        )
        info = day["shifts"].setdefault(
            shift.id,
            {
                "shift_id": shift.id,
                "shift_name": shift.name,
                "shift_type": shift.shift_type,
                "is_night": shift.is_night,
                "min_staff": shift.min_staff,
                "assigned": 0,
                "employees": [],
            },
        )
        info["assigned"] += 1
        info["employees"].append(assignment.employee_id)

    out = []
    for day in sorted(days.values(), key=lambda d: d["date"]):
        shift_list = []
        for info in day["shifts"].values():
            understaffed = info["assigned"] < info["min_staff"]
            info["understaffed"] = understaffed
            shift_list.append(info)
        day["shift_list"] = shift_list
        day["understaffed_any"] = any(s["understaffed"] for s in shift_list)
        day_ot = sum(log.overtime_hours for log in logs_by_day.get(date.fromisoformat(day["date"]), []))
        day_night = sum(log.night_hours for log in logs_by_day.get(date.fromisoformat(day["date"]), []))
        day["overtime_hours"] = round(day_ot, 2)
        day["night_hours"] = round(day_night, 2)
        day["cost_flags"] = {
            "night_differential_applies": day_night > 0,
            "overtime_applies": day_ot > 0,
            "holiday_pay_applies": day["is_holiday"],
        }
        out.append(day)
    return out
