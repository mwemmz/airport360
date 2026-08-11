"""Leave management service.

State machine: Requested -> Approved/Rejected -> Taken (approval deducts the days
from the accrual-ledger-backed balance; cancellation returns them).
Year-end close pays out leftover annual leave or carries it forward (capped).
"""
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .audit import log_action
from .deps import CurrentUser
from .models.core import Employee
from .models.hr import LeaveAccrualEntry, LeaveBalance, LeaveRequest, LeaveType

MONTHS_FACTOR = 30


def working_days_in_range(start: date, end: date, holidays: set[date] | None = None) -> int:
    """Count Mon-Fri in [start, end], optionally excluding holidays."""
    days = 0
    cur = start
    while cur <= end:
        if cur.weekday() < 5 and (holidays is None or cur not in holidays):
            days += 1
        cur += timedelta(days=1)
    return days


def _months_employed(employee: Employee, as_of: date) -> int:
    return max(0, (as_of - employee.hire_date).days // MONTHS_FACTOR)


def _balance_row(db: Session, employee_id: int, leave_type_id: int, year: int) -> LeaveBalance:
    b = db.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year == year,
        )
    )
    if b is None:
        b = LeaveBalance(employee_id=employee_id, leave_type_id=leave_type_id, year=year, available_days=0.0)
        db.add(b)
        db.flush()
    return b


def _post_entry(
    db: Session,
    employee_id: int,
    leave_type_id: int,
    year: int,
    action: str,
    days: float,
    entry_date: date,
    reference: str | None = None,
    note: str | None = None,
    created_by: int | None = None,
) -> LeaveBalance:
    balance = _balance_row(db, employee_id, leave_type_id, year)
    if action == "accrue":
        balance.accrued_days = round(balance.accrued_days + days, 4)
        balance.available_days = round(balance.available_days + days, 4)
    elif action == "taken":
        balance.taken_days = round(balance.taken_days + days, 4)
        balance.available_days = round(balance.available_days - days, 4)
    elif action == "paid_out":
        balance.paid_out_days = round(balance.paid_out_days + days, 4)
        balance.available_days = round(balance.available_days - days, 4)
    elif action == "carried_forward":
        balance.opened_days = round(balance.opened_days + days, 4)
    elif action == "adjust":
        balance.adjusted_days = round(balance.adjusted_days + days, 4)
        balance.available_days = round(balance.available_days + days, 4)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown ledger action '{action}'")
    db.add(
        LeaveAccrualEntry(
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            year=year,
            entry_date=entry_date,
            action=action,
            days=round(days, 4),
            balance_after=round(balance.available_days, 4),
            reference=reference,
            note=note,
            created_by=created_by,
        )
    )
    db.flush()
    return balance


def _next_request_number(db: Session, year: int) -> str:
    count = db.scalar(select(func.count(LeaveRequest.id))) or 0
    return f"LV-{year}-{count + 1:04d}"


def list_balances(db: Session, site_id: int, employee_id: int | None = None) -> list[dict]:
    """Balances as display rows with leave-type info attached."""
    rows = db.execute(
        select(LeaveBalance, LeaveType)
        .join(LeaveType, LeaveType.id == LeaveBalance.leave_type_id)
        .join(Employee, Employee.id == LeaveBalance.employee_id)
        .where(Employee.site_id == site_id)
        .order_by(LeaveBalance.year.desc(), LeaveType.name)
    ).all()
    out = []
    for balance, ltype in rows:
        if employee_id is not None and balance.employee_id != employee_id:
            continue
        out.append(
            {
                "id": balance.id,
                "employee_id": balance.employee_id,
                "leave_type_id": ltype.id,
                "leave_type": ltype.name,
                "leave_type_code": ltype.code,
                "year": balance.year,
                "opened_days": balance.opened_days,
                "accrued_days": balance.accrued_days,
                "taken_days": balance.taken_days,
                "adjusted_days": balance.adjusted_days,
                "paid_out_days": balance.paid_out_days,
                "available_days": balance.available_days,
            }
        )
    return out


def accrue_monthly(db: Session, current: CurrentUser, site_id: int, year: int, month: int) -> dict:
    """Run the monthly accrual for every eligible employee on the site. Idempotent:
    a month that already has an 'accrue' entry for an employee is skipped."""
    from .statutory_config import DEFAULT_RATES

    employees = db.scalars(
        select(Employee).where(Employee.site_id == site_id, Employee.employment_status == "Active")
    ).all()
    leave_types = db.scalars(select(LeaveType).where(LeaveType.active.is_(True), LeaveType.accrual_days_per_month > 0)).all()

    posted = 0
    skipped = 0
    for employee in employees:
        for ltype in leave_types:
            if employee.contract_type not in ltype.applicable_contracts:
                continue
            for m in range(1, month + 1):
                entry_date = date(year, m, 1) + timedelta(days=32)
                entry_date = entry_date.replace(day=1) - timedelta(days=1)  # last day of month m
                reference = f"accrue-{year}-{m:02d}"
                existing = db.scalar(
                    select(LeaveAccrualEntry.id).where(
                        LeaveAccrualEntry.employee_id == employee.id,
                        LeaveAccrualEntry.leave_type_id == ltype.id,
                        LeaveAccrualEntry.reference == reference,
                    )
                )
                if existing:
                    skipped += 1
                    continue
                if _months_employed(employee, entry_date) < ltype.eligible_after_months:
                    continue
                _post_entry(
                    db,
                    employee.id,
                    ltype.id,
                    year,
                    "accrue",
                    ltype.accrual_days_per_month,
                    entry_date,
                    reference=reference,
                    note=f"Monthly accrual {date(year, m, 1):%b %Y}",
                    created_by=current.user.id,
                )
                posted += 1
    db.commit()
    log_action(db, current.user.id, site_id, "run_leave_accrual", "leave_balance", None, f"year={year} month={month}", None)
    db.commit()
    return {"site_id": site_id, "year": year, "month": month, "posted_entries": posted, "already_present": skipped}


def run_year_end(db: Session, current: CurrentUser, site_id: int, year: int) -> dict:
    """Close a leave year: paid-out types cash out leftover days (ledger 'paid_out'),
    other types carry forward to the next year capped by max_carryover_days."""
    employees = db.scalars(
        select(Employee).where(Employee.site_id == site_id, Employee.employment_status == "Active")
    ).all()
    leave_types = db.scalars(select(LeaveType).where(LeaveType.active.is_(True))).all()

    paid_out = 0
    carried = 0
    for employee in employees:
        for ltype in leave_types:
            if ltype.accrual_days_per_month <= 0 and not ltype.grant_days_per_year:
                continue
            balance = _balance_row(db, employee.id, ltype.id, year)
            leftover = round(balance.opened_days + balance.accrued_days + balance.adjusted_days - balance.taken_days, 4)
            if leftover <= 0:
                continue
            if ltype.paid_out_year_end:
                ref = f"year-end-payout-{year}"
                if not db.scalar(
                    select(LeaveAccrualEntry.id).where(
                        LeaveAccrualEntry.employee_id == employee.id,
                        LeaveAccrualEntry.leave_type_id == ltype.id,
                        LeaveAccrualEntry.reference == ref,
                    )
                ):
                    _post_entry(
                        db, employee.id, ltype.id, year, "paid_out", leftover, date(year, 12, 31),
                        reference=ref, note=f"Year-end payout {year}", created_by=current.user.id,
                    )
                    paid_out += 1
            else:
                carry = leftover
                if ltype.max_carryover_days is not None:
                    carry = min(carry, ltype.max_carryover_days)
                if carry > 0:
                    ref = f"carryover-{year}-{year + 1}"
                    if not db.scalar(
                        select(LeaveAccrualEntry.id).where(
                            LeaveAccrualEntry.employee_id == employee.id,
                            LeaveAccrualEntry.leave_type_id == ltype.id,
                            LeaveAccrualEntry.reference == ref,
                        )
                    ):
                        _post_entry(
                            db, employee.id, ltype.id, year, "carried_forward", carry, date(year, 12, 31),
                            reference=ref, note=f"Carryover to {year + 1}", created_by=current.user.id,
                        )
                        next_balance = _balance_row(db, employee.id, ltype.id, year + 1)
                        next_balance.opened_days = round(next_balance.opened_days + carry, 4)
                        next_balance.available_days = round(next_balance.available_days + carry, 4)
                        carried += 1
    db.commit()
    log_action(db, current.user.id, site_id, "run_leave_year_end", "leave_balance", None, f"year={year}", None)
    db.commit()
    return {"site_id": site_id, "year": year, "paid_out_rows": paid_out, "carried_forward_rows": carried}


def create_leave_request(
    db: Session,
    current: CurrentUser,
    employee_id: int,
    leave_type_id: int,
    start_date: date,
    end_date: date,
    reason: str | None,
    requested_by_user_id: int,
    force: bool = False,
) -> LeaveRequest:
    employee = db.get(Employee, employee_id)
    if not employee or employee.site_id != current.site_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    ltype = db.get(LeaveType, leave_type_id)
    if not ltype or not ltype.active:
        raise HTTPException(status_code=404, detail="Leave type not found")
    if employee.contract_type not in ltype.applicable_contracts:
        raise HTTPException(status_code=400, detail=f"Leave type '{ltype.name}' does not apply to {employee.contract_type} contracts")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
    if ltype.eligible_after_months > 0 and _months_employed(employee, start_date) < ltype.eligible_after_months:
        raise HTTPException(
            status_code=400,
            detail=f"Not yet eligible: {ltype.name} requires {ltype.eligible_after_months} months of service",
        )

    year = start_date.year
    days = working_days_in_range(start_date, end_date)
    if days <= 0:
        raise HTTPException(status_code=400, detail="Leave period contains no working days")

    if ltype.accrual_days_per_month > 0 and not force:
        balance = _balance_row(db, employee_id, leave_type_id, year)
        if balance.available_days < days:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient {ltype.name} balance: {days} requested, {balance.available_days:.2f} available",
            )

    overlapping = db.scalar(
        select(func.count(LeaveRequest.id)).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(["Requested", "Approved"]),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
    )
    if overlapping:
        raise HTTPException(status_code=400, detail="Employee already has an overlapping leave request")

    request = LeaveRequest(
        request_number=_next_request_number(db, year),
        site_id=current.site_id,
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        start_date=start_date,
        end_date=end_date,
        days_requested=days,
        status="Requested",
        reason=reason,
        requested_by=requested_by_user_id,
    )
    db.add(request)
    db.flush()
    return request


def approve_leave(db: Session, current: CurrentUser, request: LeaveRequest) -> LeaveRequest:
    if request.status != "Requested":
        raise HTTPException(status_code=409, detail=f"Cannot approve a '{request.status}' request")
    request.status = "Approved"
    request.approver_id = current.user.id
    request.approved_at = datetime.now()
    balance = _post_entry(
        db,
        request.employee_id,
        request.leave_type_id,
        request.start_date.year,
        "taken",
        request.days_requested,
        request.start_date,
        reference=request.request_number,
        note=f"Leave {request.request_number} approved",
        created_by=current.user.id,
    )
    db.commit()
    db.refresh(request)
    return request


def reject_leave(db: Session, current: CurrentUser, request: LeaveRequest, reason: str) -> LeaveRequest:
    if request.status != "Requested":
        raise HTTPException(status_code=409, detail=f"Cannot reject a '{request.status}' request")
    request.status = "Rejected"
    request.approver_id = current.user.id
    request.approved_at = datetime.now()
    request.rejection_reason = reason
    db.commit()
    db.refresh(request)
    return request


def cancel_leave(db: Session, current: CurrentUser, request: LeaveRequest) -> LeaveRequest:
    if request.status == "Taken":
        raise HTTPException(status_code=409, detail="Cannot cancel a completed leave")
    if request.status == "Approved":
        # Return the reserved days to the balance.
        _post_entry(
            db,
            request.employee_id,
            request.leave_type_id,
            request.start_date.year,
            "adjust",
            request.days_requested,
            date.today(),
            reference=request.request_number,
            note=f"Leave {request.request_number} cancelled — days returned",
            created_by=current.user.id,
        )
    request.status = "Cancelled"
    db.commit()
    db.refresh(request)
    return request


def mark_taken(db: Session, current: CurrentUser, request: LeaveRequest) -> LeaveRequest:
    if request.status != "Approved":
        raise HTTPException(status_code=409, detail=f"Only approved leave can be marked Taken (currently '{request.status}')")
    request.status = "Taken"
    request.taken_at = datetime.now()
    db.commit()
    db.refresh(request)
    return request
