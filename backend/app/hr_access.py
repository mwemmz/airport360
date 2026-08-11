"""Shared HR access helpers (department resolution, employee name lookups)."""
from sqlalchemy.orm import Session

from .deps import CurrentUser
from .models.core import Employee


def approver_department_id(db: Session, current: CurrentUser) -> int | None:
    """Department a Department Head manages, derived from their linked employee record."""
    if not current.user.employee_id:
        return None
    emp = db.get(Employee, current.user.employee_id)
    return emp.department_id if emp else None


def my_employee_id(current: CurrentUser) -> int | None:
    return current.user.employee_id


def employee_name(db: Session, employee_id: int) -> str:
    emp = db.get(Employee, employee_id)
    if not emp:
        return f"#{employee_id}"
    return f"{emp.first_name} {emp.last_name}"
