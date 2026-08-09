from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..models.core import BudgetLine, Department, Employee, PurchaseOrder, PurchaseRequisition, Vendor
from ..schemas import (
    BudgetLineOut,
    PurchaseOrderCreate,
    PurchaseOrderOut,
    PurchaseRequisitionCreate,
    PurchaseRequisitionOut,
    VendorOut,
)
from ..security import (
    ROLE_ADMIN,
    ROLE_APPROVER,
    ROLE_EXECUTIVE,
    ROLE_FINANCE,
    ROLE_HR,
    ROLE_STAFF,
)

router = APIRouter(prefix="/procurement", tags=["procurement"])


def _next_requisition_number(db: Session) -> str:
    count = db.scalar(select(PurchaseRequisition)) or 0
    total = len(db.scalars(select(PurchaseRequisition)).all())
    return f"REQ-{datetime.now().strftime('%Y%m%d')}-{total + 1:04d}"


def _next_po_number(db: Session) -> str:
    total = len(db.scalars(select(PurchaseOrder)).all())
    return f"PO-{datetime.now().strftime('%Y%m%d')}-{total + 1:04d}"


@router.get("/requisitions", response_model=list[PurchaseRequisitionOut])
def list_requisitions(
    site_id: int | None = None,
    status_filter: str | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_APPROVER, ROLE_HR, ROLE_STAFF))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    stmt = select(PurchaseRequisition).where(PurchaseRequisition.site_id == site_id)
    if status_filter:
        stmt = stmt.where(PurchaseRequisition.status == status_filter)
    return db.scalars(stmt.order_by(PurchaseRequisition.created_at.desc())).all()


@router.post("/requisitions", response_model=PurchaseRequisitionOut, status_code=status.HTTP_201_CREATED)
def create_requisition(
    body: PurchaseRequisitionCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_HR, ROLE_STAFF))] = None,
):
    department = db.get(Department, body.department_id)
    if not department or department.site_id != current.site_id:
        raise HTTPException(status_code=400, detail="Department not found on this site")
    requester = db.get(Employee, body.requested_by_employee_id)
    if not requester or requester.site_id != current.site_id:
        raise HTTPException(status_code=400, detail="Requester not found on this site")
    if body.budget_line_id:
        bl = db.get(BudgetLine, body.budget_line_id)
        if not bl or bl.site_id != current.site_id:
            raise HTTPException(status_code=400, detail="Budget line not found on this site")

    req = PurchaseRequisition(
        requisition_number=_next_requisition_number(db),
        site_id=current.site_id,
        department_id=body.department_id,
        requested_by_employee_id=body.requested_by_employee_id,
        title=body.title,
        description=body.description,
        category=body.category,
        estimated_amount=body.estimated_amount,
        currency=body.currency,
        budget_line_id=body.budget_line_id,
        status="Submitted",
    )
    db.add(req)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_requisition", "purchase_requisition", req.id, req.requisition_number, request)
    db.commit()
    db.refresh(req)
    return req


@router.post("/requisitions/{req_id}/approve", response_model=PurchaseRequisitionOut)
def approve_requisition(
    req_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_APPROVER))] = None,
):
    req = db.get(PurchaseRequisition, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    assert_site_access(current, req.site_id)
    if req.status != "Submitted":
        raise HTTPException(status_code=409, detail=f"Cannot approve requisition in status '{req.status}'")

    req.status = "Approved"
    req.approved_by = current.user.full_name
    req.approved_at = datetime.now(timezone.utc)
    if req.budget_line_id:
        bl = db.get(BudgetLine, req.budget_line_id)
        if bl:
            bl.spent = (bl.spent or 0) + req.estimated_amount
    log_action(db, current.user.id, current.site_id, "approve_requisition", "purchase_requisition", req.id, req.requisition_number, request)
    db.commit()
    db.refresh(req)
    return req


@router.post("/requisitions/{req_id}/reject", response_model=PurchaseRequisitionOut)
def reject_requisition(
    req_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_APPROVER))] = None,
):
    req = db.get(PurchaseRequisition, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    assert_site_access(current, req.site_id)
    if req.status != "Submitted":
        raise HTTPException(status_code=409, detail=f"Cannot reject requisition in status '{req.status}'")
    req.status = "Rejected"
    log_action(db, current.user.id, current.site_id, "reject_requisition", "purchase_requisition", req.id, req.requisition_number, request)
    db.commit()
    db.refresh(req)
    return req


@router.get("/vendors", response_model=list[VendorOut])
def list_vendors(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_APPROVER, ROLE_HR, ROLE_STAFF))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    return db.scalars(select(Vendor).where(Vendor.site_id == site_id).order_by(Vendor.name)).all()


@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_APPROVER, ROLE_HR))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    return db.scalars(
        select(PurchaseOrder).where(PurchaseOrder.site_id == site_id).order_by(PurchaseOrder.created_at.desc())
    ).all()


@router.post("/purchase-orders", response_model=PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    body: PurchaseOrderCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_FINANCE))] = None,
):
    req = db.get(PurchaseRequisition, body.requisition_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requisition not found")
    assert_site_access(current, req.site_id)
    if req.status != "Approved":
        raise HTTPException(status_code=409, detail="Purchase orders can only be raised on approved requisitions")
    vendor = db.get(Vendor, body.vendor_id)
    if not vendor or vendor.site_id != current.site_id:
        raise HTTPException(status_code=400, detail="Vendor not found on this site")

    po = PurchaseOrder(
        po_number=_next_po_number(db),
        requisition_id=req.id,
        site_id=current.site_id,
        vendor_id=vendor.id,
        total_amount=body.total_amount,
        currency=body.currency,
        status="Issued",
    )
    req.status = "Ordered"
    db.add(po)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_purchase_order", "purchase_order", po.id, po.po_number, request)
    db.commit()
    db.refresh(po)
    return po


@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderOut)
def receive_purchase_order(
    po_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_FINANCE))] = None,
):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    assert_site_access(current, po.site_id)
    if po.status not in ("Issued", "Partially Received"):
        raise HTTPException(status_code=409, detail=f"Cannot receive purchase order in status '{po.status}'")
    po.status = "Received"
    po.received_at = datetime.now(timezone.utc)
    log_action(db, current.user.id, current.site_id, "receive_purchase_order", "purchase_order", po.id, po.po_number, request)
    db.commit()
    db.refresh(po)
    return po
