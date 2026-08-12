from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_action
from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..models.core import BudgetLine, Department, Expense
from ..schemas import BudgetLineOut, BudgetLineUpdate, ExpenseCreate, ExpenseOut, ExpenseUpdate
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


def _load_expense(db: Session, expense_id: int, site_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if not expense or expense.site_id != site_id:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


def _load_budget_line(db: Session, line_id: int, site_id: int) -> BudgetLine:
    line = db.get(BudgetLine, line_id)
    if not line or line.site_id != site_id:
        raise HTTPException(status_code=404, detail="Budget line not found")
    return line


def _check_department(db: Session, department_id: int, site_id: int) -> None:
    department = db.get(Department, department_id)
    if not department or department.site_id != site_id:
        raise HTTPException(status_code=400, detail="Department not found on this site")


@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    body: ExpenseUpdate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_FINANCE))] = None,
):
    expense = _load_expense(db, expense_id, current.site_id)
    old_line_id = expense.budget_line_id
    old_amount = expense.amount

    if body.department_id is not None:
        _check_department(db, body.department_id, current.site_id)
        expense.department_id = body.department_id
    if body.budget_line_id is not None:
        bl = db.get(BudgetLine, body.budget_line_id)
        if not bl or bl.site_id != current.site_id:
            raise HTTPException(status_code=400, detail="Budget line not found on this site")
        expense.budget_line_id = body.budget_line_id
    if body.category is not None:
        expense.category = body.category
    if body.vendor is not None:
        expense.vendor = body.vendor
    if body.amount is not None:
        expense.amount = body.amount
    if body.expense_date is not None:
        expense.expense_date = body.expense_date
    if body.notes is not None:
        expense.notes = body.notes

    new_line_id = expense.budget_line_id
    new_amount = expense.amount
    if old_line_id != new_line_id or old_amount != new_amount:
        if old_line_id:
            old_line = db.get(BudgetLine, old_line_id)
            if old_line:
                old_line.spent = (old_line.spent or 0) - old_amount
        if new_line_id:
            new_line = db.get(BudgetLine, new_line_id)
            if new_line:
                new_line.spent = (new_line.spent or 0) + new_amount

    log_action(db, current.user.id, current.site_id, "update_expense", "expense", expense.id, expense.expense_number, request)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_FINANCE))] = None,
):
    expense = _load_expense(db, expense_id, current.site_id)
    if expense.budget_line_id:
        line = db.get(BudgetLine, expense.budget_line_id)
        if line:
            line.spent = (line.spent or 0) - expense.amount
    log_action(db, current.user.id, current.site_id, "delete_expense", "expense", expense.id, expense.expense_number, request)
    db.delete(expense)
    db.commit()


@router.put("/budgets/{line_id}", response_model=BudgetLineOut)
def update_budget_line(
    line_id: int,
    body: BudgetLineUpdate,
    db: DbSession = None,
    request: Request = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_FINANCE))] = None,
):
    line = _load_budget_line(db, line_id, current.site_id)
    if body.department_id is not None:
        _check_department(db, body.department_id, current.site_id)
        line.department_id = body.department_id
    if body.fiscal_year is not None:
        line.fiscal_year = body.fiscal_year
    if body.category is not None:
        line.category = body.category
    if body.allocated is not None:
        if body.allocated < (line.spent or 0):
            raise HTTPException(status_code=400, detail="Allocated amount cannot be below what is already spent")
        line.allocated = body.allocated
    log_action(db, current.user.id, current.site_id, "update_budget_line", "budget_line", line.id, f"{line.category} FY{line.fiscal_year}", request)
    db.commit()
    db.refresh(line)
    return line
