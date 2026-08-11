from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..hr_access import approver_department_id, employee_name
from ..leave_service import (
    accrue_monthly,
    approve_leave,
    cancel_leave,
    create_leave_request,
    list_balances,
    mark_taken,
    reject_leave,
    run_year_end,
)
from ..models.core import Employee
from ..models.hr import LeaveRequest, LeaveType
from ..schemas import (
    AccrueIn,
    LeaveBalanceOut,
    LeaveRequestCreate,
    LeaveRequestOut,
    LeaveTypeOut,
    RejectIn,
    YearEndIn,
)
from ..security import ROLE_ADMIN, ROLE_APPROVER, ROLE_HR, ROLE_STAFF

router = APIRouter(prefix="/hr/leave", tags=["hr"])


def _serialize(db: Session, request: LeaveRequest) -> dict:
    return {
        "id": request.id,
        "request_number": request.request_number,
        "employee_id": request.employee_id,
        "employee_name": employee_name(db, request.employee_id),
        "leave_type_id": request.leave_type_id,
        "leave_type": db.get(LeaveType, request.leave_type_id).name,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "days_requested": request.days_requested,
        "status": request.status,
        "reason": request.reason,
        "rejection_reason": request.rejection_reason,
        "approved_at": request.approved_at,
        "created_at": request.created_at,
    }


def _load_request(db: Session, request_id: int) -> LeaveRequest:
    req = db.get(LeaveRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return req


def _approver_can_act(db: Session, current: CurrentUser, request: LeaveRequest) -> bool:
    """Department Head may approve/reject leave only for their own department."""
    emp = db.get(Employee, request.employee_id)
    return approver_department_id(db, current) is not None and emp.department_id == approver_department_id(db, current)


@router.get("/types", response_model=list[LeaveTypeOut])
def list_leave_types(db: DbSession = None, current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None):
    return db.scalars(select(LeaveType).where(LeaveType.active.is_(True)).order_by(LeaveType.name)).all()


@router.get("/balances", response_model=list[LeaveBalanceOut])
def get_balances(
    employee_id: int | None = None,
    year: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None,
):
    site_id = current.site_id
    if current.role == ROLE_STAFF:
        employee_id = current.user.employee_id
        if not employee_id:
            raise HTTPException(status_code=404, detail="No linked employee record")
    elif current.role == ROLE_APPROVER:
        dept = approver_department_id(db, current)
        if dept is None:
            return []
        emp_ids = db.scalars(select(Employee.id).where(Employee.department_id == dept)).all()
        rows = [b for b in list_balances(db, site_id, employee_id) if b["employee_id"] in set(emp_ids)]
        if year is not None:
            rows = [b for b in rows if b["year"] == year]
        return rows
    rows = list_balances(db, site_id, employee_id)
    if year is not None:
        rows = [b for b in rows if b["year"] == year]
    return rows


@router.post("/accrue")
def run_accrual(
    body: AccrueIn,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    result = accrue_monthly(db, current, current.site_id, body.year, body.month)
    log_action(db, current.user.id, current.site_id, "leave_accrual", "leave_balance", None, str(result), request)
    db.commit()
    return result


@router.post("/year-end")
def year_end_close(
    body: YearEndIn,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    result = run_year_end(db, current, current.site_id, body.year)
    log_action(db, current.user.id, current.site_id, "leave_year_end", "leave_balance", None, str(result), request)
    db.commit()
    return result


@router.get("/requests", response_model=list[LeaveRequestOut])
def list_requests(
    employee_id: int | None = None,
    status_filter: str | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER, ROLE_STAFF))] = None,
):
    stmt = select(LeaveRequest).where(LeaveRequest.site_id == current.site_id).order_by(LeaveRequest.created_at.desc())
    if current.role == ROLE_STAFF:
        stmt = stmt.where(LeaveRequest.employee_id == current.user.employee_id)
    elif current.role == ROLE_APPROVER:
        dept = approver_department_id(db, current)
        if dept is None:
            return []
        stmt = stmt.where(
            LeaveRequest.employee_id.in_(select(Employee.id).where(Employee.department_id == dept))
        )
    if employee_id is not None and current.role != ROLE_STAFF:
        stmt = stmt.where(LeaveRequest.employee_id == employee_id)
    if status_filter:
        stmt = stmt.where(LeaveRequest.status == status_filter)
    return [_serialize(db, req) for req in db.scalars(stmt).all()]


@router.post("/requests", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def submit_leave_request(
    body: LeaveRequestCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_STAFF))] = None,
):
    employee_id = body.employee_id
    if current.role == ROLE_STAFF:
        if current.user.employee_id != employee_id:
            raise HTTPException(status_code=403, detail="Staff may only request leave for themselves")
    req = create_leave_request(db, current, employee_id, body.leave_type_id, body.start_date, body.end_date, body.reason, current.user.id)
    log_action(db, current.user.id, current.site_id, "create_leave_request", "leave_request", req.id, req.request_number, request)
    db.commit()
    db.refresh(req)
    return _serialize(db, req)


@router.post("/requests/{request_id}/approve", response_model=LeaveRequestOut)
def approve_request(
    request_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER))] = None,
):
    req = _load_request(db, request_id)
    assert_site_access(current, req.site_id)
    if current.role == ROLE_APPROVER and not _approver_can_act(db, current, req):
        raise HTTPException(status_code=403, detail="Department Head can only approve leave in their own department")
    req = approve_leave(db, current, req)
    log_action(db, current.user.id, current.site_id, "approve_leave_request", "leave_request", req.id, req.request_number, request)
    db.commit()
    return _serialize(db, req)


@router.post("/requests/{request_id}/reject", response_model=LeaveRequestOut)
def reject_request(
    request_id: int,
    body: RejectIn,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_APPROVER))] = None,
):
    req = _load_request(db, request_id)
    assert_site_access(current, req.site_id)
    if current.role == ROLE_APPROVER and not _approver_can_act(db, current, req):
        raise HTTPException(status_code=403, detail="Department Head can only reject leave in their own department")
    req = reject_leave(db, current, req, body.reason)
    log_action(db, current.user.id, current.site_id, "reject_leave_request", "leave_request", req.id, req.request_number, request)
    db.commit()
    return _serialize(db, req)


@router.post("/requests/{request_id}/cancel", response_model=LeaveRequestOut)
def cancel_request(
    request_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_STAFF))] = None,
):
    req = _load_request(db, request_id)
    assert_site_access(current, req.site_id)
    if current.role == ROLE_STAFF and req.employee_id != current.user.employee_id:
        raise HTTPException(status_code=403, detail="Staff may only cancel their own leave requests")
    req = cancel_leave(db, current, req)
    log_action(db, current.user.id, current.site_id, "cancel_leave_request", "leave_request", req.id, req.request_number, request)
    db.commit()
    return _serialize(db, req)


@router.post("/requests/{request_id}/mark-taken", response_model=LeaveRequestOut)
def take_request(
    request_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR))] = None,
):
    req = _load_request(db, request_id)
    assert_site_access(current, req.site_id)
    req = mark_taken(db, current, req)
    log_action(db, current.user.id, current.site_id, "mark_leave_taken", "leave_request", req.id, req.request_number, request)
    db.commit()
    return _serialize(db, req)
