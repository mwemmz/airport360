"""HR module models: statutory config, leave, attendance/shifts, payroll, HR cases.

Design notes:
- Every site-scoped table carries site_id -> sites.id, matching the rest of the app.
- StatutoryConfig is national law (no site column) and is versioned by effective_date.
- Leave balances are derived from an accrual ledger (LeaveAccrualEntry) rather than a
  fixed yearly grant; LeaveBalance is a cached projection per (employee, type, year).
- Payslip rows are immutable: payroll generation never mutates an existing payslip.
All data is simulated/anonymized.
"""
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Time as SATime,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

# ---------------------------------------------------------------------------
# Statutory configuration (national, versioned by effective date)
# ---------------------------------------------------------------------------

STATUTORY_CATEGORIES = {
    "statutory_deduction": "Statutory deductions (employee/employer contributions)",
    "taxation": "Income tax (PAYE)",
    "labour_standard": "Fair labour standards (overtime, night work)",
    "leave": "Leave accrual rules (Employment Code Act 2019)",
}


class StatutoryConfig(Base):
    """One row per config key per effective date. Lookup returns the latest
    row whose effective_date <= as_of. Every rate is labelled with source and
    effective date so the UI can show where a number came from."""

    __tablename__ = "statutory_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_key: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("config_key", "effective_date", name="uq_statutory_key_effective"),)


# ---------------------------------------------------------------------------
# Leave management
# ---------------------------------------------------------------------------

LEAVE_CATEGORIES = ["annual", "sick", "maternity", "paternity", "family_responsibility", "compassionate", "study", "unpaid", "other"]
LEAVE_STATUSES = ["Requested", "Approved", "Rejected", "Cancelled", "Taken"]
LEAVE_ACTIONS = ["accrue", "taken", "carried_forward", "paid_out", "adjust"]
CONTRACT_TYPES = ["Permanent", "Fixed-Term", "Casual", "Intern"]


class LeaveType(Base):
    """Leave policy definition. Accrual rules live here for contract-aware behaviour:
    annual leave accrues monthly, statutory leaves (maternity etc.) are fixed grants."""

    __tablename__ = "leave_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=True)
    accrual_days_per_month: Mapped[float] = mapped_column(Float, default=0.0)
    grant_days_per_year: Mapped[float | None] = mapped_column(Float, nullable=True)
    eligible_after_months: Mapped[int] = mapped_column(Integer, default=0)
    max_carryover_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    paid_out_year_end: Mapped[bool] = mapped_column(Boolean, default=False)
    config_key: Mapped[str | None] = mapped_column(String(48), nullable=True)
    contract_types: Mapped[str] = mapped_column(String(160), default="Permanent,Fixed-Term,Casual,Intern")
    requires_document: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def applicable_contracts(self) -> list[str]:
        return [c.strip() for c in self.contract_types.split(",") if c.strip()]


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), index=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days_requested: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, default="Requested")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class LeaveBalance(Base):
    """Cached projection of the accrual ledger for one (employee, type, year)."""

    __tablename__ = "leave_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), index=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    opened_days: Mapped[float] = mapped_column(Float, default=0.0)
    accrued_days: Mapped[float] = mapped_column(Float, default=0.0)
    taken_days: Mapped[float] = mapped_column(Float, default=0.0)
    adjusted_days: Mapped[float] = mapped_column(Float, default=0.0)
    paid_out_days: Mapped[float] = mapped_column(Float, default=0.0)
    available_days: Mapped[float] = mapped_column(Float, default=0.0)

    __table_args__ = (UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_balance_emp_type_year"),)


class LeaveAccrualEntry(Base):
    """Single-entry accrual ledger: every movement of leave is one row."""

    __tablename__ = "leave_accrual_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), index=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    days: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Time & attendance
# ---------------------------------------------------------------------------

SHIFT_TYPES = ["day", "night", "custom"]
ATTENDANCE_SOURCES = ["manual", "system"]


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    start_time: Mapped[time] = mapped_column(SATime, nullable=False)
    end_time: Mapped[time] = mapped_column(SATime, nullable=False)
    shift_type: Mapped[str] = mapped_column(String(16), index=True, default="day")
    standard_hours: Mapped[float] = mapped_column(Float, default=8.0)
    min_staff: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def is_night(self) -> bool:
        return self.shift_type == "night"


class ShiftAssignment(Base):
    """One person on one shift on one date. Status flows Assigned -> Swapped/Cancelled."""

    __tablename__ = "shift_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"), index=True, nullable=False)
    work_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, default="Assigned")
    swapped_with_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("employee_id", "work_date", name="uq_shift_assignment_emp_day"),)


class TimeLog(Base):
    """Clock-in/clock-out pair with computed hours. The computation layer
    (attendance_service) fills regular/overtime/night/public_holiday breakdowns."""

    __tablename__ = "time_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    work_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    clock_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clock_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hours_worked: Mapped[float] = mapped_column(Float, default=0.0)
    standard_hours: Mapped[float] = mapped_column(Float, default=8.0)
    overtime_hours: Mapped[float] = mapped_column(Float, default=0.0)
    night_hours: Mapped[float] = mapped_column(Float, default=0.0)
    public_holiday: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rest_day: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(16), index=True, default="manual")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("employee_id", "work_date", name="uq_time_log_emp_day"),)


class PublicHoliday(Base):
    """National holiday calendar (site_id NULL = applies to every site)."""

    __tablename__ = "public_holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    holiday_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("holiday_date", "site_id", name="uq_public_holiday_date_site"),)


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------

PAYROLL_STATUSES = ["Draft", "Processed"]


class PayrollPeriod(Base):
    __tablename__ = "payroll_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, default="Draft")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("site_id", "period_start", "period_end", name="uq_payroll_period_site_dates"),)


class EmployeeAllowance(Base):
    __tablename__ = "employee_allowances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    allowance_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Payslip(Base):
    """Immutable payroll output. A payslip is generated once and never edited;
    the statutory rates used at generation time are snapshotted into the row."""

    __tablename__ = "payslips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payslip_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    period_id: Mapped[int] = mapped_column(ForeignKey("payroll_periods.id"), index=True, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    base_salary: Mapped[float] = mapped_column(Float, nullable=False)
    overtime_hours: Mapped[float] = mapped_column(Float, default=0.0)
    overtime_pay: Mapped[float] = mapped_column(Float, default=0.0)
    night_hours: Mapped[float] = mapped_column(Float, default=0.0)
    night_differential_pay: Mapped[float] = mapped_column(Float, default=0.0)
    public_holiday_hours: Mapped[float] = mapped_column(Float, default=0.0)
    public_holiday_pay: Mapped[float] = mapped_column(Float, default=0.0)
    leave_payout: Mapped[float] = mapped_column(Float, default=0.0)
    allowances_pay: Mapped[float] = mapped_column(Float, default=0.0)
    gross_pay: Mapped[float] = mapped_column(Float, nullable=False)

    napsa_deduction: Mapped[float] = mapped_column(Float, default=0.0)
    paye_deduction: Mapped[float] = mapped_column(Float, default=0.0)
    nhima_deduction: Mapped[float] = mapped_column(Float, default=0.0)
    total_deductions: Mapped[float] = mapped_column(Float, default=0.0)
    net_pay: Mapped[float] = mapped_column(Float, nullable=False)

    employer_napsa: Mapped[float] = mapped_column(Float, default=0.0)
    employer_nhima: Mapped[float] = mapped_column(Float, default=0.0)
    total_employer_cost: Mapped[float] = mapped_column(Float, nullable=False)

    deductions_order: Mapped[str] = mapped_column(String(40), default="NAPSA -> PAYE -> NHIMA")
    rates_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), index=True, default="Generated")
    generated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# HR case management
# ---------------------------------------------------------------------------

HR_CASE_STATUSES = ["Logged", "Under Review", "Investigating", "Resolved", "Closed"]
HR_CASE_CATEGORIES = ["grievance", "disciplinary", "harassment", "performance", "wellness", "attendance", "other"]
HR_CASE_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class HrCase(Base):
    __tablename__ = "hr_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True, nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    reporter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), index=True, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(24), index=True, default="Logged")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HrCaseNote(Base):
    """Audit trail / case file notes. Private notes are visible only to HR/Admin."""

    __tablename__ = "hr_case_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("hr_cases.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
