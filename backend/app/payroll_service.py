"""Payroll engine.

Monthly payslip per active employee:
  gross = base salary + overtime + night differential + public-holiday pay
          + leave payout + active allowances
  deductions in statutory order: NAPSA -> PAYE -> NHIMA
    - NAPSA (employee %) deducted first
    - PAYE bands applied to (gross - NAPSA)
    - NHIMA (employee %) on gross
  net = gross - NAPSA - PAYE - NHIMA
  employer cost = gross + employer NAPSA + employer NHIMA

Payslip rows are immutable: generation skips any (period, employee) that already
has a payslip, and there is no update path. The statutory rates in force at
generation time are snapshotted into each row.
"""
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .attendance_service import overtime_hours_for_period
from .audit import log_action
from .deps import CurrentUser
from .models.core import Employee
from .models.hr import EmployeeAllowance, LeaveAccrualEntry, PayrollPeriod, Payslip, TimeLog
from .statutory_config import paye_bands_from_rates, paye_tax, get_effective_rates


def get_or_create_period(db: Session, current: CurrentUser, site_id: int, period_start: date, period_end: date) -> PayrollPeriod:
    period = db.scalar(
        select(PayrollPeriod).where(
            PayrollPeriod.site_id == site_id,
            PayrollPeriod.period_start == period_start,
            PayrollPeriod.period_end == period_end,
        )
    )
    if period:
        return period
    if period_end < period_start:
        raise HTTPException(status_code=400, detail="period_end must be on or after period_start")
    period = PayrollPeriod(site_id=site_id, period_start=period_start, period_end=period_end, created_by=current.user.id)
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


def _hourly_rate(monthly_salary: float, rates: dict) -> float:
    monthly_hours = float(rates["overtime"].get("monthly_hours") or 208.0)
    return monthly_salary / monthly_hours


def _daily_rate(monthly_salary: float, rates: dict) -> float:
    working_days = float(rates["leave_annual"].get("working_days_per_month") or 26.0)
    return monthly_salary / working_days


def _leave_payout(db: Session, employee_id: int, period_start: date, period_end: date, daily_rate: float) -> float:
    days = db.scalar(
        select(func.coalesce(func.sum(LeaveAccrualEntry.days), 0.0)).where(
            LeaveAccrualEntry.employee_id == employee_id,
            LeaveAccrualEntry.action == "paid_out",
            LeaveAccrualEntry.entry_date >= period_start,
            LeaveAccrualEntry.entry_date <= period_end,
        )
    )
    return round(float(days or 0.0) * daily_rate, 2)


def build_payslip_data(db: Session, employee: Employee, period: PayrollPeriod, rates: dict | None = None) -> dict:
    rates = rates or get_effective_rates(db)
    monthly = (employee.salary or 0.0) / 12.0
    hourly = _hourly_rate(monthly, rates)
    daily = _daily_rate(monthly, rates)

    ot_hours = overtime_hours_for_period(db, period.site_id, period.period_start, period.period_end, employee.id)
    logs = db.scalars(
        select(TimeLog).where(
            TimeLog.site_id == period.site_id,
            TimeLog.employee_id == employee.id,
            TimeLog.work_date >= period.period_start,
            TimeLog.work_date <= period.period_end,
        )
    ).all()
    night_hours = round(sum(log.night_hours for log in logs), 2)
    holiday_hours = round(sum(log.hours_worked for log in logs if log.public_holiday), 2)

    allowances = db.scalars(
        select(EmployeeAllowance).where(
            EmployeeAllowance.site_id == period.site_id,
            EmployeeAllowance.employee_id == employee.id,
            EmployeeAllowance.active.is_(True),
        )
    ).all()
    allowances_pay = round(sum(a.amount for a in allowances), 2)

    leave_payout = _leave_payout(db, employee.id, period.period_start, period.period_end, daily)

    overtime_pay = round(ot_hours * hourly * float(rates["overtime"]["normal_multiplier"]), 2)
    night_diff = round(night_hours * hourly * float(rates["night_work"]["premium_rate"]), 2)
    holiday_pay = round(holiday_hours * hourly * float(rates["overtime"]["public_holiday_multiplier"]), 2)

    gross = round(monthly + overtime_pay + night_diff + holiday_pay + leave_payout + allowances_pay, 2)

    napsa = round(gross * float(rates["napsa"]["employee"]), 2)
    taxable = round(gross - napsa, 2)
    paye = paye_tax(taxable, paye_bands_from_rates(rates))
    nhima = round(gross * float(rates["nhima"]["employee"]), 2)

    total_deductions = round(napsa + paye + nhima, 2)
    net = round(gross - total_deductions, 2)

    employer_napsa = round(gross * float(rates["napsa"]["employer"]), 2)
    employer_nhima = round(gross * float(rates["nhima"]["employer"]), 2)
    employer_cost = round(gross + employer_napsa + employer_nhima, 2)

    return {
        "employee_id": employee.id,
        "base_salary": round(monthly, 2),
        "overtime_hours": round(ot_hours, 2),
        "overtime_pay": overtime_pay,
        "night_hours": night_hours,
        "night_differential_pay": night_diff,
        "public_holiday_hours": holiday_hours,
        "public_holiday_pay": holiday_pay,
        "leave_payout": leave_payout,
        "allowances_pay": allowances_pay,
        "gross_pay": gross,
        "napsa_deduction": napsa,
        "paye_deduction": paye,
        "nhima_deduction": nhima,
        "total_deductions": total_deductions,
        "net_pay": net,
        "employer_napsa": employer_napsa,
        "employer_nhima": employer_nhima,
        "total_employer_cost": employer_cost,
        "rates_snapshot": rates,
    }


def generate_payslips(db: Session, current: CurrentUser, period: PayrollPeriod) -> list[Payslip]:
    if period.status == "Processed":
        raise HTTPException(status_code=409, detail=f"Payroll period {period.id} is already processed")
    rates = get_effective_rates(db)
    employees = db.scalars(
        select(Employee).where(Employee.site_id == period.site_id, Employee.employment_status == "Active")
    ).all()

    created = []
    seq = db.scalar(select(func.count(Payslip.id))) or 0
    for employee in employees:
        existing = db.scalar(
            select(Payslip.id).where(Payslip.period_id == period.id, Payslip.employee_id == employee.id)
        )
        if existing:
            continue  # immutable — never overwrite
        seq += 1
        data = build_payslip_data(db, employee, period, rates)
        payslip = Payslip(
            payslip_number=f"PS-{period.period_start:%Y%m}-{seq:04d}",
            site_id=period.site_id,
            period_id=period.id,
            period_start=period.period_start,
            period_end=period.period_end,
            **data,
            deductions_order="NAPSA -> PAYE -> NHIMA",
            generated_by=current.user.id,
        )
        db.add(payslip)
        created.append(payslip)
    if created:
        db.flush()
    period.status = "Processed"
    period.processed_at = datetime.now()
    db.commit()
    for payslip in created:
        db.refresh(payslip)
    log_action(db, current.user.id, period.site_id, "generate_payroll", "payroll_period", period.id, f"{len(created)} payslips", None)
    db.commit()
    return created


def list_payslips(db: Session, period: PayrollPeriod) -> list[Payslip]:
    return list(db.scalars(select(Payslip).where(Payslip.period_id == period.id).order_by(Payslip.employee_id)).all())


def period_summary(db: Session, period: PayrollPeriod) -> dict:
    slips = db.scalars(select(Payslip).where(Payslip.period_id == period.id)).all()
    return {
        "period_id": period.id,
        "site_id": period.site_id,
        "period_start": period.period_start.isoformat(),
        "period_end": period.period_end.isoformat(),
        "status": period.status,
        "headcount": len(slips),
        "total_gross": round(sum(s.gross_pay for s in slips), 2),
        "total_napsa": round(sum(s.napsa_deduction for s in slips), 2),
        "total_paye": round(sum(s.paye_deduction for s in slips), 2),
        "total_nhima": round(sum(s.nhima_deduction for s in slips), 2),
        "total_deductions": round(sum(s.total_deductions for s in slips), 2),
        "total_net": round(sum(s.net_pay for s in slips), 2),
        "total_employer_cost": round(sum(s.total_employer_cost for s in slips), 2),
    }
