from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..models.core import BudgetLine, Department, Expense
from ..schemas import BudgetLineOut, ExpenseCreate, ExpenseOut
from ..security import ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/budgets", response_model=list[BudgetLineOut])
def list_budgets(
    site_id: int | None = None,
    fiscal_year: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    stmt = select(BudgetLine).where(BudgetLine.site_id == site_id)
    if fiscal_year:
        stmt = stmt.where(BudgetLine.fiscal_year == fiscal_year)
    return db.scalars(stmt.order_by(BudgetLine.category)).all()


@router.post("/budgets", response_model=BudgetLineOut, status_code=status.HTTP_201_CREATED)
def create_budget_line(
    fiscal_year: int,
    category: str,
    allocated: float,
    department_id: int | None = None,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_FINANCE))] = None,
):
    if department_id:
        department = db.get(Department, department_id)
        if not department or department.site_id != current.site_id:
            raise HTTPException(status_code=400, detail="Department not found on this site")
    line = BudgetLine(
        site_id=current.site_id,
        department_id=department_id,
        fiscal_year=fiscal_year,
        category=category,
        allocated=allocated,
        spent=0.0,
    )
    db.add(line)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_budget_line", "budget_line", line.id, f"{category} FY{fiscal_year}", request)
    db.commit()
    db.refresh(line)
    return line


@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(
    site_id: int | None = None,
    category: str | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    stmt = select(Expense).where(Expense.site_id == site_id)
    if category:
        stmt = stmt.where(Expense.category == category)
    return db.scalars(stmt.order_by(Expense.expense_date.desc())).all()


@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    body: ExpenseCreate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_FINANCE))] = None,
):
    """Record an internal expense tied to procurement/budget. Explicitly out of scope:
    no payment processing, no PCI data — internal record-keeping only."""
    department = db.get(Department, body.department_id)
    if not department or department.site_id != current.site_id:
        raise HTTPException(status_code=400, detail="Department not found on this site")
    if body.budget_line_id:
        bl = db.get(BudgetLine, body.budget_line_id)
        if not bl or bl.site_id != current.site_id:
            raise HTTPException(status_code=400, detail="Budget line not found on this site")
        bl.spent = (bl.spent or 0) + body.amount

    total = len(db.scalars(select(Expense)).all())
    expense = Expense(
        expense_number=f"EXP-{body.expense_date.isoformat().replace('-', '')}-{total + 1:04d}",
        site_id=current.site_id,
        department_id=body.department_id,
        purchase_order_id=body.purchase_order_id,
        budget_line_id=body.budget_line_id,
        category=body.category,
        vendor=body.vendor,
        amount=body.amount,
        currency=body.currency,
        expense_date=body.expense_date,
        notes=body.notes,
    )
    db.add(expense)
    db.flush()
    log_action(db, current.user.id, current.site_id, "create_expense", "expense", expense.id, expense.expense_number, request)
    db.commit()
    db.refresh(expense)
    return expense
