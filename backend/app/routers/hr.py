from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..models.core import Department, Employee, TrainingRecord
from ..schemas import (
    DepartmentOut,
    EmployeeOut,
    TrainingRecordCreate,
    TrainingRecordOut,
)
from ..security import ROLE_ADMIN, ROLE_APPROVER, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_STAFF

router = APIRouter(prefix="/hr", tags=["hr"])


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_HR, ROLE_APPROVER, ROLE_STAFF, ROLE_FINANCE))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    return db.scalars(select(Department).where(Department.site_id == site_id).order_by(Department.name)).all()


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    site_id: int | None = None,
    department_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_HR, ROLE_APPROVER))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    stmt = select(Employee).where(Employee.site_id == site_id)
    if department_id:
        stmt = stmt.where(Employee.department_id == department_id)
    return db.scalars(stmt.order_by(Employee.employee_number)).all()


@router.get("/employees/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None,
):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if emp.site_id != current.site_id and current.role not in (ROLE_ADMIN, ROLE_EXECUTIVE):
        raise HTTPException(status_code=403, detail="Cross-site access denied")
    return emp


@router.post("/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_number: str,
    first_name: str,
    last_name: str,
    email: str,
    department_id: int,
    job_title: str,
    hire_date: str,
    employment_status: str = "Active",
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    department = db.get(Department, department_id)
    if not department or department.site_id != current.site_id:
        raise HTTPException(status_code=400, detail="Department not found on this site")
    from datetime import date

    emp = Employee(
        employee_number=employee_number,
        first_name=first_name,
        last_name=last_name,
        email=email,
        site_id=current.site_id,
        department_id=department_id,
        job_title=job_title,
        employment_status=employment_status,
        hire_date=date.fromisoformat(hire_date),
    )
    db.add(emp)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_employee", "employee", emp.id, emp.employee_number, request)
    db.commit()
    db.refresh(emp)
    return emp


@router.get("/training", response_model=list[TrainingRecordOut])
def list_training(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    return db.scalars(select(TrainingRecord).where(TrainingRecord.site_id == site_id)).all()


@router.post("/training", response_model=TrainingRecordOut, status_code=status.HTTP_201_CREATED)
def create_training(
    body: TrainingRecordCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    emp = db.get(Employee, body.employee_id)
    if not emp or emp.site_id != current.site_id:
        raise HTTPException(status_code=400, detail="Employee not found on this site")
    record = TrainingRecord(
        employee_id=body.employee_id,
        site_id=current.site_id,
        course_name=body.course_name,
        provider=body.provider,
        status=body.status,
        completed_date=body.completed_date,
        certificate=body.certificate,
    )
    db.add(record)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_training", "training_record", record.id, body.course_name, request)
    db.commit()
    db.refresh(record)
    return record
