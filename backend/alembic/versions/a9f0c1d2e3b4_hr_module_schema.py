"""HR module: statutory config, leave, attendance, payroll, HR cases

Revision ID: a9f0c1d2e3b4
Revises: 38efe1b4df2f
Create Date: 2026-08-11 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a9f0c1d2e3b4'
down_revision: Union[str, None] = '38efe1b4df2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("contract_type", sa.String(24), nullable=False, server_default="Permanent"))

    op.create_table(
        "statutory_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("config_key", sa.String(48), nullable=False, index=True),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(40), nullable=False, index=True),
        sa.Column("value", sa.JSON, nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False, index=True),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("config_key", "effective_date", name="uq_statutory_key_effective"),
    )

    op.create_table(
        "leave_types",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(24), nullable=False, index=True, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(40), nullable=False, index=True),
        sa.Column("paid", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("accrual_days_per_month", sa.Float, nullable=False, server_default="0"),
        sa.Column("grant_days_per_year", sa.Float, nullable=True),
        sa.Column("eligible_after_months", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_carryover_days", sa.Float, nullable=True),
        sa.Column("paid_out_year_end", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("config_key", sa.String(48), nullable=True),
        sa.Column("contract_types", sa.String(160), nullable=False, server_default="Permanent,Fixed-Term,Casual,Intern"),
        sa.Column("requires_document", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="1"),
    )

    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_number", sa.String(32), nullable=False, index=True, unique=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False, index=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("leave_type_id", sa.Integer, sa.ForeignKey("leave_types.id"), nullable=False, index=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("days_requested", sa.Float, nullable=False),
        sa.Column("status", sa.String(24), nullable=False, index=True, server_default="Requested"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("approver_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    op.create_table(
        "leave_balances",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("leave_type_id", sa.Integer, sa.ForeignKey("leave_types.id"), nullable=False, index=True),
        sa.Column("year", sa.Integer, nullable=False, index=True),
        sa.Column("opened_days", sa.Float, nullable=False, server_default="0"),
        sa.Column("accrued_days", sa.Float, nullable=False, server_default="0"),
        sa.Column("taken_days", sa.Float, nullable=False, server_default="0"),
        sa.Column("adjusted_days", sa.Float, nullable=False, server_default="0"),
        sa.Column("paid_out_days", sa.Float, nullable=False, server_default="0"),
        sa.Column("available_days", sa.Float, nullable=False, server_default="0"),
        sa.UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_balance_emp_type_year"),
    )

    op.create_table(
        "leave_accrual_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("leave_type_id", sa.Integer, sa.ForeignKey("leave_types.id"), nullable=False, index=True),
        sa.Column("year", sa.Integer, nullable=False, index=True),
        sa.Column("entry_date", sa.Date, nullable=False, index=True),
        sa.Column("action", sa.String(24), nullable=False, index=True),
        sa.Column("days", sa.Float, nullable=False),
        sa.Column("balance_after", sa.Float, nullable=False),
        sa.Column("reference", sa.String(64), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "shifts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False, index=True),
        sa.Column("department_id", sa.Integer, sa.ForeignKey("departments.id"), nullable=True, index=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("shift_type", sa.String(16), nullable=False, index=True, server_default="day"),
        sa.Column("standard_hours", sa.Float, nullable=False, server_default="8"),
        sa.Column("min_staff", sa.Integer, nullable=False, server_default="1"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default="1"),
    )

    op.create_table(
        "shift_assignments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False, index=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("shift_id", sa.Integer, sa.ForeignKey("shifts.id"), nullable=False, index=True),
        sa.Column("work_date", sa.Date, nullable=False, index=True),
        sa.Column("status", sa.String(16), nullable=False, index=True, server_default="Assigned"),
        sa.Column("swapped_with_employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("employee_id", "work_date", name="uq_shift_assignment_emp_day"),
    )

    op.create_table(
        "time_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False, index=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("work_date", sa.Date, nullable=False, index=True),
        sa.Column("clock_in", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clock_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hours_worked", sa.Float, nullable=False, server_default="0"),
        sa.Column("standard_hours", sa.Float, nullable=False, server_default="8"),
        sa.Column("overtime_hours", sa.Float, nullable=False, server_default="0"),
        sa.Column("night_hours", sa.Float, nullable=False, server_default="0"),
        sa.Column("public_holiday", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("is_rest_day", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("source", sa.String(16), nullable=False, index=True, server_default="manual"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("employee_id", "work_date", name="uq_time_log_emp_day"),
    )

    op.create_table(
        "public_holidays",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("holiday_date", sa.Date, nullable=False, index=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("holiday_date", "site_id", name="uq_public_holiday_date_site"),
    )

    op.create_table(
        "payroll_periods",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False, index=True),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, index=True, server_default="Draft"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("site_id", "period_start", "period_end", name="uq_payroll_period_site_dates"),
    )

    op.create_table(
        "employee_allowances",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False, index=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("allowance_type", sa.String(40), nullable=False, index=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "payslips",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("payslip_number", sa.String(32), nullable=False, index=True, unique=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False, index=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("period_id", sa.Integer, sa.ForeignKey("payroll_periods.id"), nullable=False, index=True),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("base_salary", sa.Float, nullable=False),
        sa.Column("overtime_hours", sa.Float, nullable=False, server_default="0"),
        sa.Column("overtime_pay", sa.Float, nullable=False, server_default="0"),
        sa.Column("night_hours", sa.Float, nullable=False, server_default="0"),
        sa.Column("night_differential_pay", sa.Float, nullable=False, server_default="0"),
        sa.Column("public_holiday_hours", sa.Float, nullable=False, server_default="0"),
        sa.Column("public_holiday_pay", sa.Float, nullable=False, server_default="0"),
        sa.Column("leave_payout", sa.Float, nullable=False, server_default="0"),
        sa.Column("allowances_pay", sa.Float, nullable=False, server_default="0"),
        sa.Column("gross_pay", sa.Float, nullable=False),
        sa.Column("napsa_deduction", sa.Float, nullable=False, server_default="0"),
        sa.Column("paye_deduction", sa.Float, nullable=False, server_default="0"),
        sa.Column("nhima_deduction", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_deductions", sa.Float, nullable=False, server_default="0"),
        sa.Column("net_pay", sa.Float, nullable=False),
        sa.Column("employer_napsa", sa.Float, nullable=False, server_default="0"),
        sa.Column("employer_nhima", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_employer_cost", sa.Float, nullable=False),
        sa.Column("deductions_order", sa.String(40), nullable=False, server_default="NAPSA -> PAYE -> NHIMA"),
        sa.Column("rates_snapshot", sa.JSON, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, index=True, server_default="Generated"),
        sa.Column("generated_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "hr_cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_number", sa.String(32), nullable=False, index=True, unique=True),
        sa.Column("site_id", sa.Integer, sa.ForeignKey("sites.id"), nullable=False, index=True),
        sa.Column("employee_id", sa.Integer, sa.ForeignKey("employees.id"), nullable=False, index=True),
        sa.Column("reporter_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("category", sa.String(40), nullable=False, index=True),
        sa.Column("severity", sa.String(16), nullable=False, index=True, server_default="MEDIUM"),
        sa.Column("status", sa.String(24), nullable=False, index=True, server_default="Logged"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("assigned_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "hr_case_notes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("hr_cases.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("is_private", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in (
        "hr_case_notes",
        "hr_cases",
        "payslips",
        "employee_allowances",
        "payroll_periods",
        "public_holidays",
        "time_logs",
        "shift_assignments",
        "shifts",
        "leave_accrual_entries",
        "leave_balances",
        "leave_requests",
        "leave_types",
        "statutory_config",
    ):
        op.drop_table(table)
    op.drop_column("employees", "contract_type")
