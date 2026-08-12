"""HR module tests: statutory config, leave, attendance, payroll, roster, HR cases.

Uses the session-scoped seeded database. The HR seed runs a demo payroll period for
the calendar month before today, plus leave balances, time logs, and cases.
"""
from datetime import date, timedelta

from app.statutory_config import DEFAULT_RATES, paye_tax


def _staff_employee_id(client, headers) -> int:
    """The KU staff user's linked employee id (self-service reads return their own rows)."""
    resp = client.get("/v1/hr/leave/balances", headers=headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert rows, "staff user should have leave balances (seeded long-tenured employee)"
    return rows[0]["employee_id"]


def _demo_window():
    end = date(date.today().year, date.today().month, 1) - timedelta(days=1)
    start = end - timedelta(days=27)
    return start, end


# ---------------------------------------------------------------------------
# Statutory configuration
# ---------------------------------------------------------------------------

def test_paye_worked_example():
    bands = DEFAULT_RATES["paye"]["bands"]
    assert paye_tax(250, bands) == 0.0
    assert paye_tax(950, bands) == 170.0  # 125 @ 25% + 45 @ 30%
    assert paye_tax(5200, bands) == 1615.0  # 125 + 360 + 1050 + 80


def test_statutory_config_admin_read_and_rbac(admin_headers, ku_staff_headers, client):
    deny = client.get("/v1/hr/statutory-config", headers=ku_staff_headers)
    assert deny.status_code == 403

    cfg = client.get("/v1/hr/statutory-config", headers=admin_headers)
    assert cfg.status_code == 200
    keys = {row["config_key"] for row in cfg.json()}
    assert {"napsa", "nhima", "paye", "overtime", "night_work", "leave_annual"} <= keys

    effective = client.get("/v1/hr/statutory-config/effective", headers=admin_headers)
    assert effective.status_code == 200
    assert effective.json()["paye"]["bands"]

    sources = client.get("/v1/hr/statutory-config/sources", headers=admin_headers)
    assert sources.status_code == 200
    assert all(row["source"] for row in sources.json())


def test_statutory_config_admin_update_versioned(admin_headers, ku_staff_headers, client):
    payload = {
        "normal_multiplier": 1.25,
        "rest_day_multiplier": 1.5,
        "public_holiday_multiplier": 2.0,
        "weekly_threshold_hours": 48.0,
        "standard_daily_hours": 8.0,
        "monthly_hours": 208.0,
    }
    update = client.put(
        "/v1/hr/statutory-config/overtime",
        json={"value": payload, "source": "Test update", "effective_date": "2099-01-01"},
        headers=admin_headers,
    )
    assert update.status_code == 200
    assert update.json()["effective_date"] == "2099-01-01"

    deny = client.put(
        "/v1/hr/statutory-config/overtime",
        json={"value": payload, "source": "x", "effective_date": "2099-02-01"},
        headers=ku_staff_headers,
    )
    assert deny.status_code == 403


# ---------------------------------------------------------------------------
# Leave management
# ---------------------------------------------------------------------------

def test_leave_types_visible_to_staff(ku_staff_headers, client):
    resp = client.get("/v1/hr/leave/types", headers=ku_staff_headers)
    assert resp.status_code == 200
    codes = {t["code"] for t in resp.json()}
    assert {"ANL", "SICK", "MAT"} <= codes


def test_staff_balances_are_self_only(ku_staff_headers, client):
    resp = client.get("/v1/hr/leave/balances", headers=ku_staff_headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert rows
    emp_id = rows[0]["employee_id"]
    assert all(r["employee_id"] == emp_id for r in rows)
    annual = [r for r in rows if r["leave_type_code"] == "ANL"]
    assert annual and annual[0]["available_days"] >= 1


def test_leave_workflow_staff_submit_hr_approve(ku_hr_headers, ku_staff_headers, nm_hr_headers, client):
    emp_id = _staff_employee_id(client, ku_staff_headers)
    types = client.get("/v1/hr/leave/types", headers=ku_staff_headers).json()
    sick = next(t for t in types if t["code"] == "SICK")

    start = date(2099, 3, 16)
    resp = client.post(
        "/v1/hr/leave/requests",
        json={
            "employee_id": emp_id,
            "leave_type_id": sick["id"],
            "start_date": start.isoformat(),
            "end_date": date(2099, 3, 18).isoformat(),
            "reason": "test leave",
        },
        headers=ku_staff_headers,
    )
    assert resp.status_code == 201, resp.text
    req = resp.json()
    req_id = req["id"]
    assert req["status"] == "Requested"

    assert client.post(f"/v1/hr/leave/requests/{req_id}/approve", headers=ku_staff_headers).status_code == 403
    assert client.post(f"/v1/hr/leave/requests/{req_id}/approve", headers=nm_hr_headers).status_code == 403

    approved = client.post(f"/v1/hr/leave/requests/{req_id}/approve", headers=ku_hr_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "Approved"

    taken = client.post(f"/v1/hr/leave/requests/{req_id}/mark-taken", headers=ku_hr_headers)
    assert taken.status_code == 200
    assert taken.json()["status"] == "Taken"


def test_staff_only_sees_own_requests(ku_staff_headers, client):
    emp_id = _staff_employee_id(client, ku_staff_headers)
    resp = client.get("/v1/hr/leave/requests", headers=ku_staff_headers)
    assert resp.status_code == 200
    assert all(r["employee_id"] == emp_id for r in resp.json())


def test_accrual_is_idempotent(ku_hr_headers, client):
    first = client.post("/v1/hr/leave/accrue", json={"year": date.today().year, "month": 1}, headers=ku_hr_headers)
    assert first.status_code == 200, first.text
    second = client.post("/v1/hr/leave/accrue", json={"year": date.today().year, "month": 1}, headers=ku_hr_headers)
    assert second.status_code == 200
    assert second.json()["posted_entries"] == 0


def test_year_end_close(ku_hr_headers, client):
    resp = client.post("/v1/hr/leave/year-end", json={"year": date.today().year - 5}, headers=ku_hr_headers)
    assert resp.status_code == 200, resp.text
    assert "paid_out_rows" in resp.json()
    assert "carried_forward_rows" in resp.json()


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------

def test_payroll_preview_math_and_rbac(ku_hr_headers, ku_finance_headers, ku_staff_headers, client):
    year = date.today().year - 2
    period = client.post(
        "/v1/hr/payroll/periods",
        json={"period_start": date(year, 3, 1).isoformat(), "period_end": date(year, 3, 31).isoformat()},
        headers=ku_hr_headers,
    )
    assert period.status_code == 201, period.text
    period_id = period.json()["id"]

    assert client.get("/v1/hr/payroll/periods", headers=ku_finance_headers).status_code == 200
    assert client.get("/v1/hr/payroll/periods", headers=ku_staff_headers).status_code == 200

    employees = client.get("/v1/hr/employees", headers=ku_hr_headers).json()
    assert employees
    emp_id = employees[0]["id"]

    preview = client.get(f"/v1/hr/payroll/preview/{emp_id}", params={"period_id": period_id}, headers=ku_hr_headers)
    assert preview.status_code == 200, preview.text
    body = preview.json()

    gross = body["gross_pay"]
    napsa = body["napsa_deduction"]
    paye = body["paye_deduction"]
    nhima = body["nhima_deduction"]
    assert round(gross - napsa - paye - nhima, 2) == body["net_pay"]
    assert round(gross + body["employer_napsa"] + body["employer_nhima"], 2) == body["total_employer_cost"]
    assert body["gross_pay"] >= body["base_salary"]

    assert client.get(f"/v1/hr/payroll/preview/{emp_id}", params={"period_id": period_id}, headers=ku_staff_headers).status_code == 403


def test_payroll_generation_immutable_summary(ku_hr_headers, ku_finance_headers, ku_staff_headers, client):
    year = date.today().year - 2
    period = client.post(
        "/v1/hr/payroll/periods",
        json={"period_start": date(year, 4, 1).isoformat(), "period_end": date(year, 4, 30).isoformat()},
        headers=ku_hr_headers,
    )
    assert period.status_code == 201, period.text
    period_id = period.json()["id"]

    assert client.post(f"/v1/hr/payroll/periods/{period_id}/generate", headers=ku_finance_headers).status_code == 403

    generated = client.post(f"/v1/hr/payroll/periods/{period_id}/generate", headers=ku_hr_headers)
    assert generated.status_code == 200, generated.text
    slips = generated.json()
    assert slips

    # Immutable: a processed period rejects a second run.
    assert client.post(f"/v1/hr/payroll/periods/{period_id}/generate", headers=ku_hr_headers).status_code == 409

    summary = client.get(f"/v1/hr/payroll/periods/{period_id}/summary", headers=ku_hr_headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["headcount"] == len(slips)
    assert round(sum(s["net_pay"] for s in slips), 2) == body["total_net"]
    assert body["total_gross"] == round(sum(s["gross_pay"] for s in slips), 2)
    assert all(s["deductions_order"] == "NAPSA -> PAYE -> NHIMA" for s in slips)

    mine = client.get("/v1/hr/payroll/payslips/my", params={"period_id": period_id}, headers=ku_staff_headers)
    assert mine.status_code == 200, mine.text
    my_emp = mine.json()["employee_id"]
    other = next(s for s in slips if s["employee_id"] != my_emp)
    other_view = client.get(f"/v1/hr/payroll/payslips/{other['id']}", headers=ku_staff_headers)
    assert other_view.status_code == 403


# ---------------------------------------------------------------------------
# Time & attendance / roster
# ---------------------------------------------------------------------------

def test_attendance_logs_and_summary(ku_hr_headers, ku_ops_headers, ku_staff_headers, exec_headers, client):
    start, end = _demo_window()
    logs = client.get("/v1/hr/attendance/logs", params={"start": start, "end": end}, headers=ku_hr_headers)
    assert logs.status_code == 200
    assert logs.json()

    summary = client.get("/v1/hr/attendance/summary", params={"start": start, "end": end}, headers=exec_headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["total_hours"] > 0
    assert body["employees_logged"] >= 1

    cross = client.get("/v1/hr/attendance/summary", params={"start": start, "end": end, "site_id": 2}, headers=exec_headers)
    assert cross.status_code == 200
    assert cross.json()["site_id"] == 2

    assert client.get("/v1/hr/attendance/summary", params={"start": start, "end": end}, headers=ku_ops_headers).status_code == 403

    emp_id = _staff_employee_id(client, ku_staff_headers)
    staff_logs = client.get("/v1/hr/attendance/logs", params={"start": start, "end": end}, headers=ku_staff_headers)
    assert staff_logs.status_code == 200
    assert all(t["employee_id"] == emp_id for t in staff_logs.json())


def test_roster_understaffed_and_cost_flags(ku_hr_headers, ku_staff_headers, client):
    start, end = _demo_window()
    roster = client.get("/v1/hr/roster", params={"start": start, "end": end}, headers=ku_hr_headers)
    assert roster.status_code == 200
    days = roster.json()["days"]
    assert days
    assert any(d["understaffed_any"] for d in days)

    cost = client.get("/v1/hr/roster/cost", params={"start": start, "end": end}, headers=ku_hr_headers)
    assert cost.status_code == 200
    body = cost.json()
    assert body["understaffed_days"] >= 1
    assert body["total_overtime_hours"] > 0
    assert body["total_night_hours"] > 0

    assert client.get("/v1/hr/roster", params={"start": start, "end": end}, headers=ku_staff_headers).status_code == 403


def test_public_holidays(ku_hr_headers, client):
    resp = client.get("/v1/hr/attendance/holidays", headers=ku_hr_headers)
    assert resp.status_code == 200
    names = {h["name"] for h in resp.json()}
    assert "Heroes' Day" in names


# ---------------------------------------------------------------------------
# HR case management
# ---------------------------------------------------------------------------

def test_hr_cases_flow_and_rbac(auth_headers, ku_hr_headers, ku_staff_headers, exec_headers, client):
    emp_id = _staff_employee_id(client, ku_staff_headers)

    opened = client.post(
        "/v1/hr/cases",
        json={"employee_id": emp_id, "category": "grievance", "severity": "LOW", "title": "Test case", "description": "desc"},
        headers=ku_staff_headers,
    )
    assert opened.status_code == 201, opened.text
    case = opened.json()
    case_id = case["id"]
    assert case["employee_id"] == emp_id
    assert case["status"] == "Logged"

    # Another staff member cannot view this case (not the subject).
    other_staff = auth_headers("staff.ku0@airport360.com")
    assert client.get(f"/v1/hr/cases/{case_id}", headers=other_staff).status_code == 403

    # Staff can add a public note on their own case; private notes stay hidden.
    assert client.post(f"/v1/hr/cases/{case_id}/notes", json={"note": "update", "is_private": False}, headers=ku_staff_headers).status_code == 201
    assert client.post(f"/v1/hr/cases/{case_id}/notes", json={"note": "hr-only", "is_private": True}, headers=ku_hr_headers).status_code == 201

    staff_notes = client.get(f"/v1/hr/cases/{case_id}/notes", headers=ku_staff_headers)
    hr_notes = client.get(f"/v1/hr/cases/{case_id}/notes", headers=ku_hr_headers)
    assert staff_notes.status_code == 200
    assert all(not n["is_private"] for n in staff_notes.json())
    assert len(staff_notes.json()) < len(hr_notes.json())

    # HR transitions the case; staff cannot.
    trans = client.post(f"/v1/hr/cases/{case_id}/status", json={"status": "Under Review"}, headers=ku_hr_headers)
    assert trans.status_code == 200
    assert trans.json()["status"] == "Under Review"
    assert client.post(f"/v1/hr/cases/{case_id}/status", json={"status": "Resolved"}, headers=ku_staff_headers).status_code == 403

    # Executive gets aggregates only, never case files.
    analytics = client.get("/v1/hr/cases/analytics", headers=exec_headers)
    assert analytics.status_code == 200
    assert analytics.json()["total"] >= 1
    assert client.get("/v1/hr/cases", headers=exec_headers).status_code == 403


def test_employees_list_denied_for_staff(ku_staff_headers, client):
    assert client.get("/v1/hr/employees", headers=ku_staff_headers).status_code == 403


# ---------------------------------------------------------------------------
# Staff Portal (Frontline Staff shared-terminal)
# ---------------------------------------------------------------------------

def _frontline_user(db, idx=0):
    from sqlalchemy import select

    from app.models.core import User
    from app.security import ROLE_FRONTLINE

    users = [u for u in db.scalars(select(User)).all() if u.role.name == ROLE_FRONTLINE]
    assert users, "seeded frontline users expected"
    return users[idx % len(users)]


def _portal_token(client, db, idx=0):
    from app.models.core import Employee

    user = _frontline_user(db, idx)
    emp = db.get(Employee, user.employee_id)
    resp = client.post("/v1/auth/staff-portal", json={"employee_number": emp.employee_number, "pin": "1234"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["role"]["name"] == "Frontline Staff"
    return resp.json()["access_token"]


def _portal_headers(client, db, idx=0):
    return {"Authorization": f"Bearer {_portal_token(client, db, idx)}"}


def test_staff_portal_login_and_home(client, db):
    hdrs = _portal_headers(client, db)
    home = client.get("/v1/staff-portal/home", headers=hdrs)
    assert home.status_code == 200, home.text
    body = home.json()
    assert body["employee"]["employee_number"]
    assert "clock_in" in body["today"] and "clock_out" in body["today"]
    assert body["balance"], "frontline employee should have accrued leave balances"
    assert "next_shift" in body and "open_cases" in body

    shifts = client.get("/v1/staff-portal/shifts", headers=hdrs)
    assert shifts.status_code == 200


def test_staff_portal_clock_in_out(client, db):
    hdrs = _portal_headers(client, db, idx=1)
    # No log exists for today yet, so closing first must 400.
    assert client.post("/v1/staff-portal/clock", json={"action": "out"}, headers=hdrs).status_code == 400

    first = client.post("/v1/staff-portal/clock", json={"action": "in"}, headers=hdrs)
    assert first.status_code == 200, first.text
    assert first.json()["clock_in"] and first.json()["clock_out"] is None
    assert first.json()["source"] == "staff-portal"

    assert client.post("/v1/staff-portal/clock", json={"action": "in"}, headers=hdrs).status_code == 400

    second = client.post("/v1/staff-portal/clock", json={"action": "out"}, headers=hdrs)
    assert second.status_code == 200, second.text
    assert second.json()["clock_out"] and second.json()["hours_worked"] >= 0

    assert client.post("/v1/staff-portal/clock", json={"action": "out"}, headers=hdrs).status_code == 400
    assert client.post("/v1/staff-portal/clock", json={"action": "sideways"}, headers=hdrs).status_code == 422


def test_staff_portal_leave_self_service(client, db):
    from sqlalchemy import select

    from app.models.core import Employee

    hdrs = _portal_headers(client, db)
    types = client.get("/v1/staff-portal/leave-types", headers=hdrs)
    assert types.status_code == 200
    grant_type = next(t for t in types.json() if t["accrual_days_per_month"] == 0)
    assert client.get("/v1/staff-portal/balance", headers=hdrs).status_code == 200

    my_id = _frontline_user(db).employee_id
    other_id = [e.id for e in db.scalars(select(Employee)) if e.id != my_id][0]

    # Self-service endpoints never act on someone else's record.
    resp = client.post(
        "/v1/staff-portal/leave",
        json={"employee_id": other_id, "leave_type_id": grant_type["id"], "start_date": "2099-01-05", "end_date": "2099-01-06"},
        headers=hdrs,
    )
    assert resp.status_code == 403

    resp = client.post(
        "/v1/staff-portal/leave",
        json={"employee_id": my_id, "leave_type_id": grant_type["id"], "start_date": "2099-01-05", "end_date": "2099-01-06", "reason": "portal self-service"},
        headers=hdrs,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "Requested"


def test_staff_portal_case_self_service(client, db):
    from sqlalchemy import select

    from app.models.core import Employee

    hdrs = _portal_headers(client, db)
    my_id = _frontline_user(db).employee_id
    other_id = [e.id for e in db.scalars(select(Employee)) if e.id != my_id][0]

    resp = client.post(
        "/v1/staff-portal/case",
        json={"employee_id": other_id, "category": "grievance", "severity": "HIGH", "title": "nope", "description": "other"},
        headers=hdrs,
    )
    assert resp.status_code == 403

    resp = client.post(
        "/v1/staff-portal/case",
        json={"employee_id": my_id, "category": "wellness", "severity": "LOW", "title": "Lockeroom light broken", "description": "portal test"},
        headers=hdrs,
    )
    assert resp.status_code == 201, resp.text
    case_number = resp.json()["case_number"]

    mine = client.get("/v1/staff-portal/cases", headers=hdrs)
    assert mine.status_code == 200
    assert any(c["case_number"] == case_number for c in mine.json())


def test_staff_portal_denies_non_frontline(client, db, ku_staff_headers):
    from sqlalchemy import select

    from app.models.core import Employee, User
    from app.security import ROLE_FRONTLINE

    assert client.get("/v1/staff-portal/home", headers=ku_staff_headers).status_code == 403

    # An employee without any Frontline Staff account cannot use the PIN login.
    users = db.scalars(select(User)).all()
    frontline_ids = {u.employee_id for u in users if u.role.name == ROLE_FRONTLINE}
    non_front = next(u for u in users if u.employee_id and u.employee_id not in frontline_ids)
    emp = db.get(Employee, non_front.employee_id)
    assert client.post("/v1/auth/staff-portal", json={"employee_number": emp.employee_number, "pin": "1234"}).status_code == 401

    # Wrong PIN on a real frontline employee is also rejected.
    frontline_emp = db.get(Employee, _frontline_user(db).employee_id)
    assert client.post("/v1/auth/staff-portal", json={"employee_number": frontline_emp.employee_number, "pin": "9999"}).status_code == 401
