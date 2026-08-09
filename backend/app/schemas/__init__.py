from datetime import date, datetime

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
