"""Seed the database with realistic simulated data across two airport sites.

All data is simulated/anonymized. Never run against a real operator database.

Seeding runs as a series of small, individually-committed chunks. Turso's Hrana
HTTP transport drops long-lived transactions (an idle stream is closed server-side
after a short TTL, giving "404 stream not found"), so every chunk here stays a
few seconds long: a fresh connection (NullPool), a short transaction, an
immediate commit. Each chunk is also guarded, so a crashed run can be resumed —
re-running skips chunks that already committed and finishes the rest.
"""
import time
from datetime import date, datetime, timedelta
from datetime import time as day_time
from random import Random

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from .attendance_service import create_time_log
from .database import Base, TURSO_AUTH_TOKEN, engine
from .deps import CurrentUser
from .hr_cases import add_note, create_case, transition as transition_case
from .leave_service import accrue_monthly, approve_leave, create_leave_request, mark_taken
from .models.core import (
    AuditLog,
    BudgetLine,
    CapacityBuildingActivity,
    Department,
    Employee,
    Expense,
    PurchaseOrder,
    PurchaseRequisition,
    Role,
    Site,
    TrainingRecord,
    User,
    Vendor,
)
from .models.hr import (
    EmployeeAllowance,
    HrCase,
    LeaveRequest,
    LeaveType,
    PayrollPeriod,
    Payslip,
    PublicHoliday,
    Shift,
    ShiftAssignment,
    StatutoryConfig,
    TimeLog,
)
from .models.operations import (
    Alert,
    Baggage,
    BaggageScan,
    BookingReferral,
    CargoShipment,
    Complaint,
    Facility,
    Flight,
    Incident,
    MaintenanceRequest,
    Passenger,
    QueuePrediction,
    QueueSample,
    TravelAgencyPartner,
)
from .payroll_service import generate_payslips, get_or_create_period
from .security import (
    ROLE_ADMIN,
    ROLE_APPROVER,
    ROLE_EXECUTIVE,
    ROLE_FINANCE,
    ROLE_FRONTLINE,
    ROLE_HR,
    ROLE_OPS,
    ROLE_PASSENGER,
    ROLE_STAFF,
    hash_password,
)
from .statutory_config import seed_statutory_config

rng = Random(42)

# Demo payroll/attendance period = the calendar month before today (always complete).
DEMO_MONTH_END = date(date.today().year, date.today().month, 1) - timedelta(days=1)
DEMO_MONTH_START = DEMO_MONTH_END.replace(day=1)

DEPARTMENTS = ["Administration", "Operations", "Engineering", "Security", "Finance", "Customer Service", "ICT"]
JOB_TITLES = {
    "Administration": ["Admin Officer", "Executive Assistant", "Office Manager"],
    "Operations": ["Operations Officer", "Ground Ops Supervisor", "Terminal Manager"],
    "Engineering": ["Civil Engineer", "Electrical Technician", "Maintenance Engineer"],
    "Security": ["Security Officer", "Security Supervisor"],
    "Finance": ["Accountant", "Finance Officer", "Budget Analyst"],
    "Customer Service": ["Customer Service Agent", "Check-in Agent"],
    "ICT": ["IT Support Engineer", "Systems Administrator"],
}
FIRST_NAMES = ["Amina", "Tendai", "Bongani", "Chipo", "Farai", "Grace", "Tapiwa", "Nomvula", "Thabo", "Lindiwe", "Peter", "Naledi", "Sipho", "Rudo", "Moses"]
LAST_NAMES = ["Moyo", "Ndlovu", "Chirwa", "Banda", "Dube", "Phiri", "Sithole", "Mwanza", "Mumba", "Tembo", "Kabwe", "Zulu"]
VENDOR_CATEGORIES = ["Consumables", "IT Equipment", "Furniture", "Security Equipment", "Maintenance Supplies", "Office Supplies"]
CATEGORY_BUDGET = {
    "Consumables": 120_000,
    "IT Equipment": 300_000,
    "Furniture": 90_000,
    "Security Equipment": 250_000,
    "Maintenance Supplies": 180_000,
    "Office Supplies": 60_000,
}


def _seed_engine():
    if "libsql" in engine.url.drivername:
        connect_args = {"auth_token": TURSO_AUTH_TOKEN} if TURSO_AUTH_TOKEN else {}
    else:
        connect_args = {"check_same_thread": False}
    return create_engine(engine.url, connect_args=connect_args, poolclass=NullPool, pool_pre_ping=True)


# Every chunk gets a brand-new connection (fresh Hrana stream) via NullPool.
SeedSession = sessionmaker(
    bind=_seed_engine(),
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Chunk 1: sites, roles, vendors
# ---------------------------------------------------------------------------
def _seed_sites_roles_vendors(db: Session):
    if db.scalar(select(Site).limit(1)):
        return True

    sites = [
        Site(code="KU", name="Kuomboka International Airport", city="Livingstone", country="Zambia", iata_code="LVI"),
        Site(code="NM", name="Namwala Regional Airport", city="Namwala", country="Zambia", iata_code="NWA"),
    ]
    db.add_all(sites)
    db.flush()

    roles = [Role(name=r) for r in [ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_APPROVER, ROLE_STAFF, ROLE_FRONTLINE, ROLE_OPS, ROLE_PASSENGER]]
    db.add_all(roles)
    db.flush()

    for site in sites:
        vendors = []
        for cat in VENDOR_CATEGORIES:
            for i in range(2):
                vendors.append(
                    Vendor(
                        site_id=site.id,
                        name=f"{cat.split()[0]} Supply Co. {site.code}-{i + 1}",
                        category=cat,
                        contact_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                        contact_email=f"sales@{cat.lower().replace(' ', '')}{site.code}.com",
                        contact_phone=f"+26 0 97 000 {site.id}{i + 1}00",
                    )
                )
        db.add_all(vendors)
    db.commit()


# ---------------------------------------------------------------------------
# Chunk 2: departments + employees
# ---------------------------------------------------------------------------
def _seed_departments_employees(db: Session):
    if db.scalar(select(Department).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    next_emp_num = 1000
    for site in sites:
        depts = [Department(site_id=site.id, name=d, code=f"{site.code}-{d[:4].upper()}") for d in DEPARTMENTS]
        db.add_all(depts)
        db.flush()

        employees = []
        for dept in depts:
            for title in JOB_TITLES.get(dept.name, ["General Staff"]):
                employees.append(
                    Employee(
                        employee_number=f"EMP-{site.code}-{next_emp_num}",
                        first_name=rng.choice(FIRST_NAMES),
                        last_name=rng.choice(LAST_NAMES),
                        email=f"emp{next_emp_num}@{site.code.lower()}.airport360.local",
                        site_id=site.id,
                        department_id=dept.id,
                        job_title=title,
                        employment_status="Active",
                        hire_date=date.today() - timedelta(days=rng.randint(120, 1200)),
                        salary=round(rng.uniform(25_000, 80_000), 2),
                    )
                )
                next_emp_num += 1
        db.add_all(employees)
        db.flush()
    db.commit()


# ---------------------------------------------------------------------------
# Chunk 3: budget lines
# ---------------------------------------------------------------------------
def _seed_budget_lines(db: Session):
    if db.scalar(select(BudgetLine).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    departments = list(db.scalars(select(Department).order_by(Department.id)))
    departments_by_site: dict[int, list[Department]] = {}
    for dept in departments:
        departments_by_site.setdefault(dept.site_id, []).append(dept)

    budget_lines = []
    for site in sites:
        for dept in departments_by_site[site.id]:
            for cat, amt in CATEGORY_BUDGET.items():
                budget_lines.append(
                    BudgetLine(
                        site_id=site.id,
                        department_id=dept.id,
                        fiscal_year=date.today().year,
                        category=cat,
                        allocated=round(amt * rng.uniform(0.8, 1.2), 2),
                        spent=0.0,
                    )
                )
    db.add_all(budget_lines)
    db.commit()


# ---------------------------------------------------------------------------
# Chunk 4: expenses (8 weeks of history for BI trends/anomalies)
# ---------------------------------------------------------------------------
def _seed_expenses(db: Session):
    if db.scalar(select(Expense).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    departments = list(db.scalars(select(Department).order_by(Department.id)))
    budget_lines = list(db.scalars(select(BudgetLine).order_by(BudgetLine.id)))

    departments_by_site: dict[int, list[Department]] = {}
    for dept in departments:
        departments_by_site.setdefault(dept.site_id, []).append(dept)
    lines_by_site: dict[int, list[BudgetLine]] = {}
    for line in budget_lines:
        lines_by_site.setdefault(line.site_id, []).append(line)

    expenses = []
    exp_no = 1
    for site in sites:
        for _ in range(90):
            dept = rng.choice(departments_by_site[site.id])
            line = rng.choice([l for l in lines_by_site[site.id] if l.department_id == dept.id])
            amount = round(rng.uniform(800, line.allocated / 40), 2)
            expenses.append(
                Expense(
                    expense_number=f"EXP-{site.code}-{exp_no:04d}",
                    site_id=site.id,
                    department_id=dept.id,
                    budget_line_id=line.id,
                    category=line.category,
                    vendor=f"{line.category.split()[0]} Supply Co.",
                    amount=amount,
                    currency="USD",
                    expense_date=date.today() - timedelta(days=rng.randint(0, 55)),
                )
            )
            line.spent += amount
            exp_no += 1
    db.add_all(expenses)
    db.commit()


# ---------------------------------------------------------------------------
# Chunk 5: requisitions
# ---------------------------------------------------------------------------
def _seed_requisitions(db: Session):
    if db.scalar(select(PurchaseRequisition).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    departments = list(db.scalars(select(Department).order_by(Department.id)))
    employees = list(db.scalars(select(Employee).order_by(Employee.id)))
    budget_lines = list(db.scalars(select(BudgetLine).order_by(BudgetLine.id)))

    departments_by_site: dict[int, list[Department]] = {}
    for dept in departments:
        departments_by_site.setdefault(dept.site_id, []).append(dept)
    employees_by_site: dict[int, list[Employee]] = {}
    for emp in employees:
        employees_by_site.setdefault(emp.site_id, []).append(emp)
    lines_by_site: dict[int, list[BudgetLine]] = {}
    for line in budget_lines:
        lines_by_site.setdefault(line.site_id, []).append(line)

    reqs = []
    req_no = 1
    for site in sites:
        for _ in range(12):
            dept = rng.choice(departments_by_site[site.id])
            requester = rng.choice(employees_by_site[site.id])
            cat = rng.choice(VENDOR_CATEGORIES)
            amount = round(rng.uniform(1_000, 60_000), 2)
            reqs.append(
                PurchaseRequisition(
                    requisition_number=f"REQ-{site.code}-{req_no:04d}",
                    site_id=site.id,
                    department_id=dept.id,
                    requested_by_employee_id=requester.id,
                    title=f"{cat} procurement for {dept.name}",
                    description=f"Simulated requisition for {cat.lower()}",
                    category=cat,
                    estimated_amount=amount,
                    currency="USD",
                    budget_line_id=rng.choice([l for l in lines_by_site[site.id] if l.department_id == dept.id]).id,
                    status=rng.choices(["Approved", "Ordered", "Received", "Submitted", "Rejected"], weights=[4, 2, 3, 2, 1])[0],
                    approved_by=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}" if rng.random() > 0.3 else None,
                    approved_at=datetime.now() - timedelta(days=rng.randint(1, 40)),
                    created_at=datetime.now() - timedelta(days=rng.randint(1, 40)),
                )
            )
            req_no += 1
    db.add_all(reqs)
    db.commit()


# ---------------------------------------------------------------------------
# Chunk 6: purchase orders for approved requisitions
# ---------------------------------------------------------------------------
def _seed_purchase_orders(db: Session):
    if db.scalar(select(PurchaseOrder).limit(1)):
        return True

    reqs = list(db.scalars(select(PurchaseRequisition).order_by(PurchaseRequisition.id)))
    vendors = list(db.scalars(select(Vendor).order_by(Vendor.id)))

    pos = []
    po_no = 1
    for req in reqs:
        if req.status in ("Ordered", "Received"):
            vendor = rng.choice([v for v in vendors if v.site_id == req.site_id])
            pos.append(
                PurchaseOrder(
                    po_number=f"PO-{req.site_id}-{po_no:04d}",
                    requisition_id=req.id,
                    site_id=req.site_id,
                    vendor_id=vendor.id,
                    total_amount=req.estimated_amount,
                    currency="USD",
                    status="Received" if req.status == "Received" else "Issued",
                    received_at=datetime.now() - timedelta(days=rng.randint(1, 30)) if req.status == "Received" else None,
                    created_at=req.created_at + timedelta(days=1),
                )
            )
            po_no += 1
    db.add_all(pos)
    db.commit()


# ---------------------------------------------------------------------------
# Chunk 7: training records + capacity building activities
# ---------------------------------------------------------------------------
def _seed_trainings_activities(db: Session):
    if db.scalar(select(TrainingRecord).limit(1)) and db.scalar(select(CapacityBuildingActivity).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    employees = list(db.scalars(select(Employee).order_by(Employee.id)))
    employees_by_site: dict[int, list[Employee]] = {}
    for emp in employees:
        employees_by_site.setdefault(emp.site_id, []).append(emp)

    trainings = []
    for site in sites:
        for emp in employees_by_site[site.id][:14]:
            for course in ["Airport Safety Induction", "ERP User Training", "Customer Service Excellence", "Financial Reporting Basics"]:
                completed = rng.random() > 0.2
                trainings.append(
                    TrainingRecord(
                        employee_id=emp.id,
                        site_id=site.id,
                        course_name=course,
                        provider="ZACL University Partnership",
                        status="Completed" if completed else "In Progress",
                        completed_date=date.today() - timedelta(days=rng.randint(10, 120)) if completed else None,
                        certificate=rng.random() > 0.4,
                    )
                )
    db.add_all(trainings)

    activities = []
    for site in sites:
        for module in ["HR", "Procurement", "Finance", "BI", "Platform Core"]:
            for atype, cat in [("Workshop", "Student"), ("Project Work", "Student"), ("Certification", "Staff"), ("Internship", "Student")]:
                activities.append(
                    CapacityBuildingActivity(
                        site_id=site.id,
                        activity_type=atype,
                        title=f"{atype}: {module} module deployment at {site.name}",
                        participant_category=cat,
                        participants_count=rng.randint(4, 25),
                        module_area=module,
                        status=rng.choices(["Completed", "In Progress", "Planned"], weights=[5, 3, 2])[0],
                        start_date=date.today() - timedelta(days=rng.randint(0, 120)),
                        end_date=date.today() - timedelta(days=rng.randint(0, 100)) if rng.random() > 0.3 else None,
                        notes="Simulated partnership progress record.",
                    )
                )
    db.add_all(activities)
    db.commit()


# ---------------------------------------------------------------------------
# Chunk 8: users (one per role at each site + shared admin/executive)
# ---------------------------------------------------------------------------
def _seed_users(db: Session):
    if db.scalar(select(User).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    roles = list(db.scalars(select(Role).order_by(Role.id)))
    employees = list(db.scalars(select(Employee).order_by(Employee.id)))
    employees_by_site: dict[int, list[Employee]] = {}
    for emp in employees:
        employees_by_site.setdefault(emp.site_id, []).append(emp)

    role_map = {r.name: r for r in roles}
    slug = {
        ROLE_ADMIN: "admin",
        ROLE_EXECUTIVE: "executive",
        ROLE_HR: "hr",
        ROLE_FINANCE: "finance",
        ROLE_APPROVER: "depthead",
        ROLE_STAFF: "staff",
        ROLE_OPS: "ops",
        ROLE_PASSENGER: "passenger",
    }
    user_specs = [
        (ROLE_ADMIN, sites[0], "System Administrator"),
        (ROLE_EXECUTIVE, sites[0], "Executive Director"),
    ]
    for site in sites:
        user_specs.append((ROLE_HR, site, f"HR Officer {site.code}"))
        user_specs.append((ROLE_FINANCE, site, f"Finance Officer {site.code}"))
        user_specs.append((ROLE_APPROVER, site, f"Department Head {site.code}"))
        user_specs.append((ROLE_STAFF, site, f"Staff Member {site.code}"))
        user_specs.append((ROLE_OPS, site, f"Operations Manager {site.code}"))
        user_specs.append((ROLE_PASSENGER, site, f"Passenger {site.code}"))

    users = []
    for role_name, site, label in user_specs:
        site_employees = employees_by_site.get(site.id, [])
        if role_name == ROLE_STAFF and site_employees:
            # Longest-tenured employee so the staff self-service demo has balances.
            employee_id = max(site_employees, key=lambda e: e.hire_date).id
        else:
            employee_id = rng.choice(site_employees).id if site_employees else None
        users.append(
            User(
                email=f"{slug[role_name]}.{site.code.lower()}@airport360.com",
                full_name=label,
                hashed_password=hash_password("Demo1234!"),
                role_id=role_map[role_name].id,
                site_id=site.id,
                employee_id=employee_id,
            )
        )
    # Extra staff users so every role is reachable
    for site in sites:
        for i, emp in enumerate(employees_by_site[site.id][15:18]):
            users.append(
                User(
                    email=f"staff.{site.code.lower()}{i}@airport360.com",
                    full_name=f"{emp.first_name} {emp.last_name}",
                    hashed_password=hash_password("Demo1234!"),
                    role_id=role_map[ROLE_STAFF].id,
                    site_id=site.id,
                    employee_id=emp.id,
                )
            )
    # Frontline Staff kiosk users: shared-terminal PIN login, PIN = 1234.
    # Frontline Staff kiosk users: shared-terminal PIN login, PIN = 1234.
    # Deterministically the first two Security Officers per site (e.g. EMP-KU-1009)
    # so demo credentials stay stable. The kiosk auth query filters by role, so a
    # shared employee record can never be confused with a non-frontline account.
    frontline_users = []
    for site in sites:
        frontline_emps = [
            e for e in employees_by_site.get(site.id, []) if e.job_title == "Security Officer"
        ]
        for i, emp in enumerate(frontline_emps[:2]):
            frontline_users.append(
                User(
                    email=f"kiosk.{site.code.lower()}{i}@airport360.com",
                    full_name=f"{emp.first_name} {emp.last_name}",
                    hashed_password=hash_password("Demo1234!"),
                    pin_hash=hash_password("1234"),
                    role_id=role_map[ROLE_FRONTLINE].id,
                    site_id=site.id,
                    employee_id=emp.id,
                )
            )
    users.extend(frontline_users)
    db.add_all(users)
    db.commit()


# ---------------------------------------------------------------------------
# Chunk 9: flights
# ---------------------------------------------------------------------------
def _seed_flights(db: Session):
    if db.scalar(select(Flight).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    airlines = ["ZamLink Air", "KuAir", "SouthLakes", "Tropic Sky", "CargoWest"]
    route_pairs = [("LVI", "JNB"), ("JNB", "LVI"), ("LVI", "LUN"), ("LUN", "LVI"), ("LVI", "NBO"), ("NBO", "LVI"), ("LVI", "HRE"), ("HRE", "LVI")]

    for site in sites:
        flights = []
        for i in range(36):
            origin, destination = rng.choice(route_pairs)
            dep = datetime.now() + timedelta(hours=rng.randint(-20, 18))
            status = rng.choices(
                ["Scheduled", "Boarding", "Departed", "Arrived", "Delayed", "Cancelled"],
                weights=[4, 2, 3, 3, 2, 1],
            )[0]
            flights.append(
                Flight(
                    site_id=site.id,
                    flight_number=f"{site.code}{100 + i}",
                    airline=rng.choice(airlines),
                    origin=origin,
                    destination=destination,
                    scheduled_departure=dep,
                    scheduled_arrival=dep + timedelta(hours=rng.randint(1, 4)),
                    actual_departure=dep + timedelta(minutes=10) if status in ("Departed", "Arrived") else None,
                    actual_arrival=dep + timedelta(hours=rng.randint(1, 4)) if status == "Arrived" else None,
                    status=status,
                    gate=f"A{rng.randint(1, 12)}" if rng.random() > 0.2 else None,
                    terminal=f"T{rng.randint(1, 2)}",
                    passenger_capacity=180,
                    passengers_booked=rng.randint(60, 178),
                )
            )
        db.add_all(flights)
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 10: passengers
# ---------------------------------------------------------------------------
def _seed_passengers(db: Session):
    if db.scalar(select(Passenger).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    for site in sites:
        flights = list(db.scalars(select(Flight).where(Flight.site_id == site.id).order_by(Flight.id)))
        passengers = []
        pn = 1
        for flight in flights[:26]:
            for _ in range(rng.randint(8, 22)):
                passengers.append(
                    Passenger(
                        site_id=site.id,
                        flight_id=flight.id,
                        passenger_reference=f"PASS-{site.code}-{pn:04d}",
                        status=rng.choices(["Checked In", "Boarded", "In Transit"], weights=[5, 3, 2])[0],
                    )
                )
                pn += 1
        db.add_all(passengers)
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 11: baggage + scans
# ---------------------------------------------------------------------------
def _seed_baggage(db: Session):
    if db.scalar(select(Baggage).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    scan_events = ["Drop-off", "Checked", "Screening", "Sorting", "Loaded", "Transferred", "Arrived", "Delivered"]

    for site in sites:
        flights = {f.id: f for f in db.scalars(select(Flight).where(Flight.site_id == site.id).order_by(Flight.id))}
        passengers = list(db.scalars(select(Passenger).where(Passenger.site_id == site.id).order_by(Passenger.id)))

        bn = 1
        for passenger in passengers[:120]:
            flight = flights.get(passenger.flight_id)
            if not flight:
                continue
            bag_status = rng.choices(["Processing", "In Transit", "Loaded", "Arrived", "Delivered", "Missing", "Delayed"], weights=[4, 3, 3, 3, 3, 1, 1])[0]
            bag = Baggage(
                site_id=site.id,
                flight_id=flight.id,
                bag_id=f"{site.code}-BAG-{bn:05d}",
                passenger_reference=passenger.passenger_reference,
                origin=flight.origin,
                destination=flight.destination,
                status=bag_status,
                current_location=rng.choice(["Check-in", "Screening", "Sorting Hall", "Aircraft", "Carousel 1", "Carousel 2"]),
                expected_location="Carousel 1",
                exception_type=("Missing scan" if bag_status == "Missing" else "Short transfer" if bag_status == "Delayed" else None),
                transfer_time_minutes=round(rng.uniform(15, 80), 1) if rng.random() > 0.5 else None,
                risk_score=round(rng.uniform(0.0, 0.9), 2),
            )
            db.add(bag)
            db.flush()
            for i, ev in enumerate(scan_events[: rng.randint(3, 6)]):
                db.add(
                    BaggageScan(
                        baggage_id=bag.id,
                        scan_event=ev,
                        location=bag.current_location if i == 0 else f"Station {i}",
                        scanned_at=datetime.now() - timedelta(minutes=rng.randint(0, 180)),
                    )
                )
            bn += 1
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 12: queue samples
# ---------------------------------------------------------------------------
def _seed_queues(db: Session):
    if db.scalar(select(QueueSample).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    for site in sites:
        for qtype, loc in [("security", "Security Checkpoint 1"), ("checkin", "Check-in Hall"), ("immigration", "Immigration Hall")]:
            for _ in range(14):
                db.add(
                    QueueSample(
                        site_id=site.id,
                        queue_type=qtype,
                        location=loc,
                        current_length=rng.randint(3, 45),
                        avg_wait_minutes=round(rng.uniform(4, 38), 1),
                        open_counters=rng.randint(1, 6),
                        processing_rate=round(rng.uniform(0.5, 2.5), 2),
                        recorded_at=datetime.now() - timedelta(minutes=rng.randint(0, 420)),
                    )
                )
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 13: incidents
# ---------------------------------------------------------------------------
def _seed_incidents(db: Session):
    if db.scalar(select(Incident).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    for site in sites:
        inc_no = 1
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "HIGH"]:
            reported = datetime.now() - timedelta(hours=rng.randint(1, 30))
            db.add(
                Incident(
                    site_id=site.id,
                    incident_number=f"INC-{site.code}-{inc_no:04d}",
                    category=rng.choice(["security", "medical", "fire", "equipment", "passenger issue", "operational disruption"]),
                    severity=severity,
                    status="Reported",
                    title=f"{severity.title()} {rng.choice(['baggage belt outage', 'escalator fault', 'medical response', 'security breach drill', 'boarding gate delay', 'runway debris'])}",
                    description="Simulated incident for operational intelligence demonstration.",
                    location=f"Terminal {rng.randint(1, 2)}, {rng.choice(['departures', 'arrivals', 'airside'])}",
                    reported_by="ops.ku@airport360.com",
                    source="Staff",
                    reported_at=reported,
                    resolved_at=reported + timedelta(hours=1) if rng.random() > 0.4 else None,
                )
            )
            inc_no += 1
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 14: maintenance requests
# ---------------------------------------------------------------------------
def _seed_maintenance(db: Session):
    if db.scalar(select(MaintenanceRequest).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    for site in sites:
        mtn_no = 1
        for cat, loc in [("toilet", "Toilet Block A"), ("escalator", "Escalator B"), ("lighting", "Car Park Lighting")]:
            for _ in range(rng.randint(2, 3)):
                db.add(
                    MaintenanceRequest(
                        site_id=site.id,
                        request_number=f"MTN-{site.code}-{mtn_no:04d}",
                        category=cat,
                        priority=rng.choices(["High", "Medium", "Low"], weights=[3, 5, 2])[0],
                        status=rng.choices(["Reported", "In Progress", "Resolved"], weights=[3, 2, 4])[0],
                        location=loc,
                        description=f"Simulated maintenance issue at {loc}.",
                        technician="J. Mwanza",
                        reported_by="ops.ku@airport360.com",
                        source="Staff",
                        cost=round(rng.uniform(50, 1200), 2),
                        reported_at=datetime.now() - timedelta(days=rng.randint(0, 20)),
                        resolved_at=datetime.now() - timedelta(days=rng.randint(0, 15)),
                        repeat_key=f"{cat.lower()}|{loc.lower()}",
                    )
                )
                mtn_no += 1
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 15: cargo shipments
# ---------------------------------------------------------------------------
def _seed_cargo(db: Session):
    if db.scalar(select(CargoShipment).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    for site in sites:
        for i in range(10):
            db.add(
                CargoShipment(
                    site_id=site.id,
                    awb_number=f"AWB-{site.code}-{1000 + i}",
                    status=rng.choices(["Registered", "In Warehouse", "Cleared", "Released"], weights=[3, 3, 2, 2])[0],
                    origin=rng.choice(["LVI", "JNB", "NBO", "HRE"]),
                    destination=rng.choice(["LVI", "JNB", "NBO", "HRE"]),
                    weight_kg=round(rng.uniform(50, 900), 2),
                    volume_m3=round(rng.uniform(0.2, 4.5), 2),
                    storage_location=f"Bay {rng.randint(1, 8)}",
                    delayed=rng.random() > 0.7,
                    registered_at=datetime.now() - timedelta(days=rng.randint(0, 10)),
                )
            )
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 16: facilities
# ---------------------------------------------------------------------------
def _seed_facilities(db: Session):
    if db.scalar(select(Facility).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    for site in sites:
        for name in ["Terminal 1", "Terminal 2", "Control Tower", "Main Runway", "Cargo Warehouse"]:
            db.add(
                Facility(
                    site_id=site.id,
                    name=name,
                    facility_type=rng.choice(["terminal", "airfield", "operations", "cargo"]),
                    location=f"{site.name} complex",
                    status="Operational",
                )
            )
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 17: alerts
# ---------------------------------------------------------------------------
def _seed_alerts(db: Session):
    if db.scalar(select(Alert).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    for site in sites:
        db.add(
            Alert(
                site_id=site.id,
                severity="HIGH",
                alert_type="congestion",
                title="Check-in congestion predicted",
                detail="Prototype queue model forecast HIGH congestion at Check-in Hall within 30 minutes.",
                status="Active",
                trigger_key="congestion|Check-in congestion predicted",
            )
        )
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 18: complaints
# ---------------------------------------------------------------------------
def _seed_complaints(db: Session):
    if db.scalar(select(Complaint).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    for site in sites:
        cmp_no = 1
        for i in range(4):
            db.add(
                Complaint(
                    site_id=site.id,
                    complaint_number=f"CMP-{site.code}-{cmp_no:04d}",
                    passenger_reference=f"PASS-{site.code}-{100 + i:04d}",
                    category=rng.choice(["baggage", "delay", "staff", "facilities", "cleanliness"]),
                    status=rng.choices(["Submitted", "Under Review", "Resolved"], weights=[3, 2, 3])[0],
                    title=f"{rng.choice(['Delayed baggage', 'Unclean facilities', 'Long queue', 'Staff assistance'])} at {site.code}",
                    description="Simulated passenger complaint for complaint-to-incident flow.",
                    submitted_at=datetime.now() - timedelta(days=rng.randint(0, 9)),
                )
            )
            cmp_no += 1
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 19: booking marketplace partners + referrals
# ---------------------------------------------------------------------------
def _seed_partners_bookings(db: Session):
    if db.scalar(select(TravelAgencyPartner).limit(1)):
        return True

    partners = [
        TravelAgencyPartner(name="Zambia Travel Hub", website="https://zambiatravelhub.example.com", certified=True, security_endorsed=True, commission_rate=3.5, active=True),
        TravelAgencyPartner(name="Victoria Falls Tours", website="https://vicfallstours.example.com", certified=True, security_endorsed=False, commission_rate=2.8, active=True),
        TravelAgencyPartner(name="Southern Skies Travel", website="https://southernskies.example.com", certified=False, security_endorsed=True, commission_rate=4.0, active=True),
        TravelAgencyPartner(name="Kafue Safari Agency", website="https://kafuesafari.example.com", certified=True, security_endorsed=True, commission_rate=3.0, active=True),
    ]
    db.add_all(partners)
    db.flush()

    airlines = ["ZamLink Air", "KuAir", "SouthLakes", "Tropic Sky", "CargoWest"]
    sites = list(db.scalars(select(Site).order_by(Site.id)))
    for site in sites:
        for i in range(6):
            partner = rng.choice(partners)
            db.add(
                BookingReferral(
                    site_id=site.id,
                    passenger_reference=f"PASS-{site.code}-{100 + i:04d}",
                    partner_id=partner.id,
                    airline=rng.choice(airlines),
                    flight_search={"origin": rng.choice(["LVI", "LUN"]), "destination": rng.choice(["JNB", "NBO", "HRE"])},
                    redirect_url=partner.website,
                    commission_estimate=partner.commission_rate,
                    clicked_at=datetime.now() - timedelta(days=rng.randint(0, 14)),
                )
            )
    db.commit()


# ---------------------------------------------------------------------------
# Chunk 20: HR foundations — statutory config, leave types, shifts, holidays
# ---------------------------------------------------------------------------
def _seed_hr_foundations(db: Session):
    if db.scalar(select(LeaveType).limit(1)):
        return True

    seed_statutory_config(db)

    leave_types = [
        LeaveType(code="ANL", name="Annual Leave", category="annual", paid=True, accrual_days_per_month=2.0, eligible_after_months=6, max_carryover_days=15.0, paid_out_year_end=True, config_key="leave_annual", contract_types="Permanent,Fixed-Term"),
        LeaveType(code="SICK", name="Sick Leave", category="sick", paid=True, grant_days_per_year=26.0, requires_document=True, contract_types="Permanent,Fixed-Term,Casual"),
        LeaveType(code="MAT", name="Maternity Leave", category="maternity", paid=True, grant_days_per_year=120.0, contract_types="Permanent,Fixed-Term"),
        LeaveType(code="PAT", name="Paternity Leave", category="paternity", paid=True, grant_days_per_year=10.0, contract_types="Permanent,Fixed-Term"),
        LeaveType(code="FAM", name="Family Responsibility", category="family_responsibility", paid=True, grant_days_per_year=5.0),
        LeaveType(code="COM", name="Compassionate Leave", category="compassionate", paid=True, grant_days_per_year=5.0),
        LeaveType(code="STU", name="Study Leave", category="study", paid=False, grant_days_per_year=20.0),
        LeaveType(code="UNP", name="Unpaid Leave", category="unpaid", paid=False),
    ]
    db.add_all(leave_types)
    db.flush()

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    shift_specs = [
        ("Day", day_time(8, 0), day_time(16, 0), "day", 8.0, 3),
        ("Morning", day_time(6, 0), day_time(14, 0), "day", 8.0, 2),
        ("Afternoon", day_time(14, 0), day_time(22, 0), "day", 8.0, 2),
        ("Night", day_time(18, 0), day_time(6, 0), "night", 8.0, 2),
    ]
    for site in sites:
        for name, s, e, stype, hours, minstaff in shift_specs:
            db.add(Shift(site_id=site.id, name=name, start_time=s, end_time=e, shift_type=stype, standard_hours=hours, min_staff=minstaff))

    holidays = [
        PublicHoliday(name="New Year's Day", holiday_date=date(2026, 1, 1)),
        PublicHoliday(name="Good Friday", holiday_date=date(2026, 4, 3)),
        PublicHoliday(name="Labour Day", holiday_date=date(2026, 5, 1)),
        PublicHoliday(name="Africa Freedom Day", holiday_date=date(2026, 5, 25)),
        PublicHoliday(name="Heroes' Day", holiday_date=date(2026, 7, 6)),
        PublicHoliday(name="Independence Day", holiday_date=date(2026, 10, 24)),
        PublicHoliday(name="Christmas Day", holiday_date=date(2026, 12, 25)),
    ]
    db.add_all(holidays)
    db.commit()


# ---------------------------------------------------------------------------
# Chunk 21: leave balances + a small request workflow demo
# ---------------------------------------------------------------------------
def _seed_hr_leave(db: Session):
    if db.scalar(select(LeaveRequest).limit(1)):
        return True

    annual = db.scalar(select(LeaveType).where(LeaveType.code == "ANL"))
    sick = db.scalar(select(LeaveType).where(LeaveType.code == "SICK"))
    sites = list(db.scalars(select(Site).order_by(Site.id)))
    employees = list(db.scalars(select(Employee).order_by(Employee.id)))
    employees_by_site: dict[int, list[Employee]] = {}
    for emp in employees:
        employees_by_site.setdefault(emp.site_id, []).append(emp)

    for site in sites:
        hr_user = db.scalar(select(User).where(User.email == f"hr.{site.code.lower()}@airport360.com"))
        staff_user = db.scalar(select(User).where(User.email == f"staff.{site.code.lower()}@airport360.com"))
        if not hr_user:
            continue
        current = CurrentUser(hr_user, site)
        requester_id = staff_user.id if staff_user else hr_user.id

        # Accrue annual leave for every eligible employee first so balances exist
        # for the demo requests and for self-service views.
        accrue_monthly(db, current, site.id, DEMO_MONTH_END.year, DEMO_MONTH_END.month)

        eligible = [
            e for e in employees_by_site.get(site.id, [])
            if (DEMO_MONTH_END - e.hire_date).days // 30 >= 6
        ]
        scenarios = [
            ("taken", eligible[0], annual, DEMO_MONTH_END - timedelta(days=21), DEMO_MONTH_END - timedelta(days=17)),
            ("approved", eligible[1] if len(eligible) > 1 else eligible[0], annual, DEMO_MONTH_END + timedelta(days=5), DEMO_MONTH_END + timedelta(days=9)),
            ("requested", eligible[2] if len(eligible) > 2 else eligible[0], sick, DEMO_MONTH_END - timedelta(days=7), DEMO_MONTH_END - timedelta(days=5)),
        ]
        for action, emp, ltype, start, end in scenarios:
            if not emp:
                continue
            try:
                req = create_leave_request(db, current, emp.id, ltype.id, start, end, f"Simulated {ltype.name.lower()} request", requester_id)
                if action == "taken":
                    req = approve_leave(db, current, req)
                    req = mark_taken(db, current, req)
                elif action == "approved":
                    req = approve_leave(db, current, req)
            except HTTPException:
                db.rollback()
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 22: shift roster + time logs for the demo month
# ---------------------------------------------------------------------------
def _seed_hr_attendance(db: Session):
    if db.scalar(select(ShiftAssignment).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    employees = list(db.scalars(select(Employee).order_by(Employee.id)))
    employees_by_site: dict[int, list[Employee]] = {}
    for emp in employees:
        employees_by_site.setdefault(emp.site_id, []).append(emp)
    shifts = list(db.scalars(select(Shift).order_by(Shift.site_id, Shift.id)))
    shifts_by_site: dict[int, list[Shift]] = {}
    for s in shifts:
        shifts_by_site.setdefault(s.site_id, []).append(s)

    for site in sites:
        hr_user = db.scalar(select(User).where(User.email == f"hr.{site.code.lower()}@airport360.com"))
        if not hr_user:
            continue
        day_shift = next(s for s in shifts_by_site[site.id] if s.name == "Day")
        night_shift = next(s for s in shifts_by_site[site.id] if s.name == "Night")
        site_employees = sorted(employees_by_site.get(site.id, []), key=lambda e: e.id)
        night_worker_ids = {e.id for e in site_employees[:3]}

        # Last Saturday before the demo month end — covered by a single night worker
        # so the roster shows an intentional understaffed day.
        understaffed_day = DEMO_MONTH_END - timedelta(days=(DEMO_MONTH_END.weekday() - 5) % 7)
        start = DEMO_MONTH_END - timedelta(days=27)

        cur = start
        while cur <= DEMO_MONTH_END:
            for emp in site_employees:
                is_night = emp.id in night_worker_ids
                if is_night:
                    if cur.weekday() >= 6:
                        continue
                    if cur == understaffed_day and emp != site_employees[0]:
                        continue
                    shift = night_shift
                    clock_in = datetime.combine(cur, day_time(18, 0))
                    clock_out = datetime.combine(cur + timedelta(days=1), day_time(6, 0))
                else:
                    if cur.weekday() >= 5:
                        continue
                    shift = day_shift
                    clock_in = datetime.combine(cur, day_time(9, 0))
                    clock_out = datetime.combine(cur, day_time(17, 0))
                db.add(
                    ShiftAssignment(
                        site_id=site.id,
                        employee_id=emp.id,
                        shift_id=shift.id,
                        work_date=cur,
                        created_by=hr_user.id,
                    )
                )
                create_time_log(db, hr_user.id, site.id, emp.id, cur, clock_in, clock_out, shift.id, notes="Simulated attendance")
            cur += timedelta(days=1)
        db.commit()


# ---------------------------------------------------------------------------
# Chunk 23: payroll — allowances + a processed demo period with payslips
# ---------------------------------------------------------------------------
def _seed_hr_payroll(db: Session):
    if db.scalar(select(PayrollPeriod).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    employees = list(db.scalars(select(Employee).order_by(Employee.id)))
    employees_by_site: dict[int, list[Employee]] = {}
    for emp in employees:
        employees_by_site.setdefault(emp.site_id, []).append(emp)
    admin = db.scalar(select(User).where(User.email == "admin.ku@airport360.com"))

    for site in sites:
        if not admin:
            continue
        current = CurrentUser(admin, site)
        for emp in employees_by_site.get(site.id, [])[:4]:
            db.add(EmployeeAllowance(site_id=site.id, employee_id=emp.id, allowance_type="Housing", amount=300.0))
        db.commit()
        period = get_or_create_period(db, current, site.id, DEMO_MONTH_START, DEMO_MONTH_END)
        generate_payslips(db, current, period)


# ---------------------------------------------------------------------------
# Chunk 24: HR cases with a note trail across statuses
# ---------------------------------------------------------------------------
def _seed_hr_cases(db: Session):
    if db.scalar(select(HrCase).limit(1)):
        return True

    sites = list(db.scalars(select(Site).order_by(Site.id)))
    employees = list(db.scalars(select(Employee).order_by(Employee.id)))
    employees_by_site: dict[int, list[Employee]] = {}
    for emp in employees:
        employees_by_site.setdefault(emp.site_id, []).append(emp)

    for site in sites:
        hr_user = db.scalar(select(User).where(User.email == f"hr.{site.code.lower()}@airport360.com"))
        staff_user = db.scalar(select(User).where(User.email == f"staff.{site.code.lower()}@airport360.com"))
        if not hr_user:
            continue
        current = CurrentUser(hr_user, site)
        site_employees = employees_by_site.get(site.id, [])

        subject = staff_user.employee_id if staff_user and staff_user.employee_id else (site_employees[0].id if site_employees else None)
        if subject:
            case = create_case(db, current, site.id, subject, "grievance", "Shift allocation complaint", "Employee feels the roster allocation is unbalanced.", "MEDIUM")
            add_note(db, current, case, "Gathering more detail from the employee.", is_private=True)

        if len(site_employees) > 1:
            case2 = create_case(db, current, site.id, site_employees[1].id, "performance", "Quarterly performance review", "Pending performance conversation.", "LOW")
            transition_case(db, current, case2, "Under Review")

        if len(site_employees) > 2:
            create_case(db, current, site.id, site_employees[2].id, "wellness", "Wellness check-in", "Follow-up after extended sick leave.", "LOW")

        if len(site_employees) > 3:
            case4 = create_case(db, current, site.id, site_employees[3].id, "attendance", "Repeated late clock-ins", "Several late clock-ins this month.", "MEDIUM")
            transition_case(db, current, case4, "Investigating")

        db.commit()


def _run_chunk(name: str, fn):
    for attempt in range(1, 4):
        db: Session = SeedSession()
        try:
            if fn(db):
                print(f"[seed] {name}: already present, skipping.")
            return
        except Exception as exc:
            db.rollback()
            print(f"[seed] {name}: attempt {attempt} of 3 failed: {exc}")
            if attempt == 3:
                raise
        finally:
            db.close()
        time.sleep(5 * attempt)


def _summary() -> str:
    db: Session = SeedSession()
    try:
        def count(model) -> int:
            return db.scalar(select(func.count()).select_from(model)) or 0

        return (
            f"Seeded {count(Site)} sites, {count(Employee)} employees, "
            f"{count(Expense)} expenses, {count(PurchaseRequisition)} requisitions, "
            f"{count(Flight)} flights, {count(Baggage)} bags, "
            f"{count(TimeLog)} time logs, {count(Payslip)} payslips, {count(HrCase)} HR cases."
        )
    finally:
        db.close()


def seed_all() -> None:
    Base.metadata.create_all(bind=engine)
    _run_chunk("sites_roles_vendors", _seed_sites_roles_vendors)
    _run_chunk("departments_employees", _seed_departments_employees)
    _run_chunk("budget_lines", _seed_budget_lines)
    _run_chunk("expenses", _seed_expenses)
    _run_chunk("requisitions", _seed_requisitions)
    _run_chunk("purchase_orders", _seed_purchase_orders)
    _run_chunk("trainings_activities", _seed_trainings_activities)
    _run_chunk("users", _seed_users)
    _run_chunk("flights", _seed_flights)
    _run_chunk("passengers", _seed_passengers)
    _run_chunk("baggage", _seed_baggage)
    _run_chunk("queues", _seed_queues)
    _run_chunk("incidents", _seed_incidents)
    _run_chunk("maintenance", _seed_maintenance)
    _run_chunk("cargo", _seed_cargo)
    _run_chunk("facilities", _seed_facilities)
    _run_chunk("alerts", _seed_alerts)
    _run_chunk("complaints", _seed_complaints)
    _run_chunk("partners_bookings", _seed_partners_bookings)
    _run_chunk("hr_foundations", _seed_hr_foundations)
    _run_chunk("hr_leave", _seed_hr_leave)
    _run_chunk("hr_attendance", _seed_hr_attendance)
    _run_chunk("hr_payroll", _seed_hr_payroll)
    _run_chunk("hr_cases", _seed_hr_cases)
    print(_summary())


if __name__ == "__main__":
    seed_all()
