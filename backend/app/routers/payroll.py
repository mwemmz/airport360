from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..models.core import Employee
from ..models.hr import EmployeeAllowance, PayrollPeriod, Payslip
from ..payroll_service import (
    build_payslip_data,
    generate_payslips,
    get_or_create_period,
    list_payslips,
    period_summary,
)
from ..schemas import (
    EmployeeAllowanceCreate,
    EmployeeAllowanceOut,
    PayrollPeriodCreate,
    PayrollPeriodOut,
    PayslipOut,
)
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_STAFF

router = APIRouter(prefix="/hr/payroll", tags=["hr"])


def _load_period(db: Session, period_id: int) -> PayrollPeriod:
    period = db.get(PayrollPeriod, period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Payroll period not found")
    return period


@router.get("/periods", response_model=list[PayrollPeriodOut])
def list_periods(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_HR, ROLE_FINANCE, ROLE_STAFF))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    return db.scalars(select(PayrollPeriod).where(PayrollPeriod.site_id == site_id).order_by(PayrollPeriod.period_end.desc())).all()


@router.post("/periods", response_model=PayrollPeriodOut, status_code=status.HTTP_201_CREATED)
def create_period(
    body: PayrollPeriodCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    period = get_or_create_period(db, current, current.site_id, body.period_start, body.period_end)
    log_action(db, current.user.id, current.site_id, "create_payroll_period", "payroll_period", period.id, f"{body.period_start}..{body.period_end}", request)
    db.commit()
    db.refresh(period)
    return period


@router.get("/periods/{period_id}/summary")
def period_summary_endpoint(
    period_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_HR, ROLE_FINANCE))] = None,
):
    period = _load_period(db, period_id)
    assert_site_access(current, period.site_id)
    return period_summary(db, period)


@router.get("/periods/{period_id}/payslips", response_model=list[PayslipOut])
def get_period_payslips(
    period_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_FINANCE))] = None,
):
    period = _load_period(db, period_id)
    assert_site_access(current, period.site_id)
    return list_payslips(db, period)


@router.post("/periods/{period_id}/generate", response_model=list[PayslipOut])
def run_payroll(
    period_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    period = _load_period(db, period_id)
    assert_site_access(current, period.site_id)
    slips = generate_payslips(db, current, period)
    log_action(db, current.user.id, current.site_id, "generate_payroll", "payroll_period", period.id, f"{len(slips)} payslips", request)
    db.commit()
    return slips


@router.get("/payslips/my", response_model=PayslipOut)
def my_payslip(
    period_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_STAFF))] = None,
):
    """Staff self-service: their own payslip for a period (read-only)."""
    if not current.user.employee_id:
        raise HTTPException(status_code=404, detail="No linked employee record")
    period = _load_period(db, period_id)
    assert_site_access(current, period.site_id)
    payslip = db.scalar(
        select(Payslip).where(Payslip.period_id == period_id, Payslip.employee_id == current.user.employee_id)
    )
    if not payslip:
        raise HTTPException(status_code=404, detail="No payslip found for this period")
    return payslip


@router.get("/payslips/{payslip_id}", response_model=PayslipOut)
def get_payslip(
    payslip_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_FINANCE, ROLE_STAFF))] = None,
):
    payslip = db.get(Payslip, payslip_id)
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    assert_site_access(current, payslip.site_id)
    if current.role == ROLE_STAFF and payslip.employee_id != current.user.employee_id:
        raise HTTPException(status_code=403, detail="You can only view your own payslip")
    return payslip


@router.get("/allowances", response_model=list[EmployeeAllowanceOut])
def list_allowances(
    employee_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_FINANCE, ROLE_STAFF))] = None,
):
    stmt = select(EmployeeAllowance).where(EmployeeAllowance.site_id == current.site_id).order_by(EmployeeAllowance.employee_id)
    if employee_id is not None:
        stmt = stmt.where(EmployeeAllowance.employee_id == employee_id)
    if current.role == ROLE_STAFF:
        if not current.user.employee_id:
            return []
        stmt = stmt.where(EmployeeAllowance.employee_id == current.user.employee_id)
    return db.scalars(stmt).all()


@router.post("/allowances", response_model=EmployeeAllowanceOut, status_code=status.HTTP_201_CREATED)
def add_allowance(
    body: EmployeeAllowanceCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    emp = db.get(Employee, body.employee_id)
    if not emp or emp.site_id != current.site_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    allowance = EmployeeAllowance(
        site_id=current.site_id,
        employee_id=body.employee_id,
        allowance_type=body.allowance_type,
        amount=body.amount,
        active=body.active,
        notes=body.notes,
    )
    db.add(allowance)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_allowance", "employee_allowance", allowance.id, f"{body.allowance_type}", request)
    db.commit()
    db.refresh(allowance)
    return allowance


@router.get("/preview/{employee_id}")
def preview_payslip(
    employee_id: int,
    period_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    """Dry-run the payroll computation for one employee (no row written)."""
    period = _load_period(db, period_id)
    assert_site_access(current, period.site_id)
    emp = db.get(Employee, employee_id)
    if not emp or emp.site_id != period.site_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {
        "employee_id": employee_id,
        "period_id": period_id,
        **build_payslip_data(db, emp, period),
        "is_preview": True,
    }
