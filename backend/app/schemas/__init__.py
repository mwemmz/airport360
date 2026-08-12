from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SiteBase(BaseModel):
    code: str
    name: str
    city: str
    country: str
    iata_code: str | None = None


class SiteCreate(SiteBase):
    pass


class SiteOut(SiteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    active: bool
    created_at: datetime


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: RoleOut
    site_id: int
    active: bool


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=8)
    role: str
    site_id: int
    employee_id: int | None = None


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_number: str
    first_name: str
    last_name: str
    email: str
    site_id: int
    department_id: int
    job_title: str
    employment_status: str
    hire_date: date


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    name: str
    code: str


class TrainingRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    site_id: int
    course_name: str
    provider: str
    status: str
    completed_date: date | None
    certificate: bool


class TrainingRecordCreate(BaseModel):
    employee_id: int
    course_name: str
    provider: str
    status: str = "Completed"
    completed_date: date | None = None
    certificate: bool = False


class CapacityActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    activity_type: str
    title: str
    participant_category: str
    participants_count: int
    module_area: str
    status: str
    start_date: date
    end_date: date | None
    notes: str | None


class CapacityActivityCreate(BaseModel):
    activity_type: str
    title: str
    participant_category: str
    participants_count: int = 0
    module_area: str
    status: str = "Planned"
    start_date: date
    end_date: date | None = None
    notes: str | None = None


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    name: str
    category: str
    contact_name: str | None
    active: bool


class BudgetLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    department_id: int | None
    fiscal_year: int
    category: str
    allocated: float
    spent: float


class PurchaseRequisitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    requisition_number: str
    site_id: int
    department_id: int
    requested_by_employee_id: int
    title: str
    description: str | None
    category: str
    estimated_amount: float
    currency: str
    budget_line_id: int | None
    status: str
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime


class PurchaseRequisitionCreate(BaseModel):
    department_id: int
    requested_by_employee_id: int
    title: str
    description: str | None = None
    category: str
    estimated_amount: float
    currency: str = "USD"
    budget_line_id: int | None = None


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    po_number: str
    requisition_id: int
    site_id: int
    vendor_id: int
    total_amount: float
    currency: str
    status: str
    created_at: datetime
    received_at: datetime | None


class PurchaseOrderCreate(BaseModel):
    requisition_id: int
    vendor_id: int
    total_amount: float
    currency: str = "USD"


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    expense_number: str
    site_id: int
    department_id: int
    purchase_order_id: int | None
    budget_line_id: int | None
    category: str
    vendor: str
    amount: float
    currency: str
    expense_date: date


class ExpenseCreate(BaseModel):
    department_id: int
    purchase_order_id: int | None = None
    budget_line_id: int | None = None
    category: str
    vendor: str
    amount: float
    currency: str = "USD"
    expense_date: date
    notes: str | None = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    site_id: int
    action: str
    entity_type: str
    entity_id: int | None
    detail: str | None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class StaffPortalLoginIn(BaseModel):
    """Staff portal entry point: employee number + short numeric PIN (Frontline Staff only)."""
    employee_number: str
    pin: str


class StaffPortalClockIn(BaseModel):
    action: str = Field(pattern="^(in|out)$")


# ---------------------------------------------------------------------------
# HR module schemas
# ---------------------------------------------------------------------------


class StatutoryConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    config_key: str
    display_name: str
    category: str
    value: dict
    effective_date: date
    source: str
    description: str | None
    created_at: datetime


class StatutoryConfigUpdate(BaseModel):
    value: dict
    source: str = "Administrative update"
    effective_date: date | None = None


class LeaveTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    category: str
    paid: bool
    accrual_days_per_month: float
    grant_days_per_year: float | None
    eligible_after_months: int
    max_carryover_days: float | None
    paid_out_year_end: bool
    contract_types: str
    requires_document: bool
    active: bool


class LeaveBalanceOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    leave_type: str
    leave_type_code: str
    year: int
    opened_days: float
    accrued_days: float
    taken_days: float
    adjusted_days: float
    paid_out_days: float
    available_days: float


class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type_id: int
    start_date: date
    end_date: date
    reason: str | None = None


class LeaveRequestOut(BaseModel):
    id: int
    request_number: str
    employee_id: int
    employee_name: str
    leave_type_id: int
    leave_type: str
    start_date: date
    end_date: date
    days_requested: float
    status: str
    reason: str | None
    rejection_reason: str | None
    approved_at: datetime | None
    created_at: datetime


class AccrueIn(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)


class YearEndIn(BaseModel):
    year: int


class RejectIn(BaseModel):
    reason: str


class ShiftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    department_id: int | None
    name: str
    start_time: time
    end_time: time
    shift_type: str
    standard_hours: float
    min_staff: int
    is_night: bool
    description: str | None
    active: bool


class ShiftCreate(BaseModel):
    name: str
    start_time: str
    end_time: str
    shift_type: str = "day"
    standard_hours: float = 8.0
    min_staff: int = 1
    department_id: int | None = None
    description: str | None = None


class ShiftAssignmentCreate(BaseModel):
    employee_id: int
    shift_id: int
    work_date: date
    note: str | None = None


class ShiftAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    employee_id: int
    shift_id: int
    work_date: date
    status: str
    swapped_with_employee_id: int | None
    note: str | None
    created_at: datetime


class TimeLogCreate(BaseModel):
    employee_id: int
    work_date: date
    clock_in: datetime
    clock_out: datetime
    shift_id: int | None = None
    notes: str | None = None


class TimeLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    work_date: date
    clock_in: datetime
    clock_out: datetime | None
    hours_worked: float
    standard_hours: float
    overtime_hours: float
    night_hours: float
    public_holiday: bool
    is_rest_day: bool
    source: str
    notes: str | None


class PayrollPeriodCreate(BaseModel):
    period_start: date
    period_end: date


class PayrollPeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    period_start: date
    period_end: date
    status: str
    processed_at: datetime | None
    created_at: datetime


class PayslipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    payslip_number: str
    site_id: int
    employee_id: int
    period_id: int
    period_start: date
    period_end: date
    base_salary: float
    overtime_hours: float
    overtime_pay: float
    night_hours: float
    night_differential_pay: float
    public_holiday_hours: float
    public_holiday_pay: float
    leave_payout: float
    allowances_pay: float
    gross_pay: float
    napsa_deduction: float
    paye_deduction: float
    nhima_deduction: float
    total_deductions: float
    net_pay: float
    employer_napsa: float
    employer_nhima: float
    total_employer_cost: float
    deductions_order: str
    status: str
    generated_at: datetime


class EmployeeAllowanceCreate(BaseModel):
    employee_id: int
    allowance_type: str
    amount: float
    active: bool = True
    notes: str | None = None


class EmployeeAllowanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    allowance_type: str
    amount: float
    active: bool
    notes: str | None


class HrCaseCreate(BaseModel):
    employee_id: int
    category: str = "other"
    severity: str = "MEDIUM"
    title: str
    description: str | None = None


class HrCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    case_number: str
    site_id: int
    employee_id: int
    reporter_user_id: int
    category: str
    severity: str
    status: str
    title: str
    description: str | None
    assigned_user_id: int | None
    resolution_notes: str | None
    opened_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class HrCaseNoteCreate(BaseModel):
    note: str
    is_private: bool = False


class HrCaseNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    case_id: int
    user_id: int
    note: str
    is_private: bool
    created_at: datetime


class HrCaseTransition(BaseModel):
    status: str
    resolution_notes: str | None = None


class HrCaseAssign(BaseModel):
    assignee_user_id: int
