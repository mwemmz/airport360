from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from ..deps import CurrentUser, DbSession, assert_site_access, require_roles
from ..models.core import (
    BudgetLine,
    CapacityBuildingActivity,
    Employee,
    Expense,
    PurchaseRequisition,
    Site,
    TrainingRecord,
)
from ..security import ROLE_ADMIN, ROLE_APPROVER, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR

router = APIRouter(prefix="/bi", tags=["bi"])


def _anomaly_flag(amount: float, site_avg: float, factor: float = 2.5) -> dict:
    """Rule-based anomaly flag (Phase 1 low-risk AI landing): a spend is flagged when it
    exceeds `factor`x the site's recent average for that category. Transparent rule, no model."""
    is_anomaly = site_avg > 0 and amount > site_avg * factor
    return {
        "is_anomaly": is_anomaly,
        "threshold": round(site_avg * factor, 2) if site_avg > 0 else 0,
        "rule": f"spend > {factor}x the site's average for this category (avg={round(site_avg, 2)})",
    }


@router.get("/overview")
def overview(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_APPROVER))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)

    headcount = db.scalar(select(func.count(Employee.id)).where(Employee.site_id == site_id, Employee.employment_status == "Active")) or 0
    trainings_completed = db.scalar(
        select(func.count(TrainingRecord.id)).where(TrainingRecord.site_id == site_id, TrainingRecord.status == "Completed")
    ) or 0
    total_requisitions = db.scalar(select(func.count(PurchaseRequisition.id)).where(PurchaseRequisition.site_id == site_id)) or 0
    pending_approvals = db.scalar(
        select(func.count(PurchaseRequisition.id)).where(PurchaseRequisition.site_id == site_id, PurchaseRequisition.status == "Submitted")
    ) or 0
    total_spend = db.scalar(select(func.sum(Expense.amount)).where(Expense.site_id == site_id)) or 0
    total_budget = db.scalar(select(func.sum(BudgetLine.allocated)).where(BudgetLine.site_id == site_id)) or 0

    return {
        "site_id": site_id,
        "headcount": headcount,
        "trainings_completed": trainings_completed,
        "total_requisitions": total_requisitions,
        "pending_approvals": pending_approvals,
        "total_spend": round(total_spend, 2),
        "total_budget": round(total_budget, 2),
        "budget_utilization": round(total_spend / total_budget * 100, 1) if total_budget else 0,
    }


@router.get("/spend-trend")
def spend_trend(
    days: int = 30,
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_APPROVER))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    since = date.today() - timedelta(days=days)
    rows = db.execute(
        select(Expense.expense_date, func.sum(Expense.amount))
        .where(Expense.site_id == site_id, Expense.expense_date >= since)
        .group_by(Expense.expense_date)
    ).all()
    return [{"date": d.isoformat(), "amount": round(float(a), 2)} for d, a in rows]


@router.get("/spend-by-category")
def spend_by_category(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_APPROVER))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    rows = db.execute(
        select(Expense.category, func.sum(Expense.amount))
        .where(Expense.site_id == site_id)
        .group_by(Expense.category)
    ).all()
    return [{"category": c, "amount": round(float(a), 2)} for c, a in rows]


@router.get("/spend-by-site")
def spend_by_site(
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE))] = None,
):
    rows = db.execute(
        select(Expense.site_id, func.sum(Expense.amount)).group_by(Expense.site_id)
    ).all()
    return [{"site_id": s, "amount": round(float(a), 2)} for s, a in rows]


@router.get("/budget-vs-actual")
def budget_vs_actual(
    site_id: int | None = None,
    fiscal_year: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_APPROVER))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    stmt = select(BudgetLine).where(BudgetLine.site_id == site_id)
    if fiscal_year:
        stmt = stmt.where(BudgetLine.fiscal_year == fiscal_year)
    lines = db.scalars(stmt).all()
    return [
        {
            "id": line.id,
            "category": line.category,
            "fiscal_year": line.fiscal_year,
            "allocated": line.allocated,
            "spent": round(line.spent, 2),
            "utilization_pct": round(line.spent / line.allocated * 100, 1) if line.allocated else 0,
        }
        for line in lines
    ]


@router.get("/anomalies")
def anomalies(
    days: int = 30,
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_APPROVER))] = None,
):
    """Rule-based anomaly flags on procurement spend. Every flag carries the rule that fired."""
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    since = date.today() - timedelta(days=days)
    expenses = db.scalars(
        select(Expense).where(Expense.site_id == site_id, Expense.expense_date >= since)
    ).all()

    avg_by_category: dict[str, float] = defaultdict(float)
    counts: Counter[str] = Counter()
    for e in expenses:
        avg_by_category[e.category] += e.amount
        counts[e.category] += 1
    for c in avg_by_category:
        avg_by_category[c] = avg_by_category[c] / counts[c] if counts[c] else 0

    flags = []
    for e in expenses:
        flag = _anomaly_flag(e.amount, avg_by_category[e.category])
        if flag["is_anomaly"]:
            flags.append(
                {
                    "expense_id": e.id,
                    "expense_number": e.expense_number,
                    "category": e.category,
                    "amount": e.amount,
                    "expense_date": e.expense_date.isoformat(),
                    "flag": flag,
                }
            )
    return flags


@router.get("/hr-trends")
def hr_trends(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_APPROVER))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    headcount_by_dept = db.execute(
        select(Employee.department_id, func.count(Employee.id))
        .where(Employee.site_id == site_id, Employee.employment_status == "Active")
        .group_by(Employee.department_id)
    ).all()
    training_by_status = db.execute(
        select(TrainingRecord.status, func.count(TrainingRecord.id))
        .where(TrainingRecord.site_id == site_id)
        .group_by(TrainingRecord.status)
    ).all()
    return {
        "headcount_by_department": [{"department_id": d, "count": c} for d, c in headcount_by_dept],
        "training_by_status": [{"status": s, "count": c} for s, c in training_by_status],
    }


@router.get("/capacity-building")
def capacity_building_overview(
    site_id: int | None = None,
    db: DbSession = None,
    current: Annotated[CurrentUser, Depends(require_roles(ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_APPROVER))] = None,
):
    if site_id is None:
        site_id = current.site_id
    assert_site_access(current, site_id)
    rows = db.execute(
        select(CapacityBuildingActivity.status, func.count(CapacityBuildingActivity.id))
        .where(CapacityBuildingActivity.site_id == site_id)
        .group_by(CapacityBuildingActivity.status)
    ).all()
    by_module = db.execute(
        select(CapacityBuildingActivity.module_area, func.count(CapacityBuildingActivity.id))
        .where(CapacityBuildingActivity.site_id == site_id)
        .group_by(CapacityBuildingActivity.module_area)
    ).all()
    return {
        "by_status": [{"status": s, "count": c} for s, c in rows],
        "by_module": [{"module": m, "count": c} for m, c in by_module],
    }
