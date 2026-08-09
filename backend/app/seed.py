"""Seed the database with realistic simulated data across two airport sites.

All data is simulated/anonymized. Never run against a real operator database.
"""
from datetime import date, datetime, timedelta
from random import Random

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
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
from .security import ROLE_ADMIN, ROLE_APPROVER, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_STAFF, hash_password

rng = Random(42)

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


def _dates():
    return [date.today() - timedelta(days=d) for d in range(60)]


def seed_all() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        if db.scalar(select(Site).limit(1)):
            print("Database already seeded; skipping.")
            return

        sites = [
            Site(code="KU", name="Kuomboka International Airport", city="Livingstone", country="Zambia", iata_code="LVI"),
            Site(code="NM", name="Namwala Regional Airport", city="Namwala", country="Zambia", iata_code="NWA"),
        ]
        db.add_all(sites)
        db.flush()

        roles = [Role(name=r) for r in [ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_APPROVER, ROLE_STAFF]]
        db.add_all(roles)
        db.flush()

        vendors_by_site = {}
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
            vendors_by_site[site.id] = vendors
        db.flush()

        departments_by_site: dict[int, list[Department]] = {}
        employees_by_site: dict[int, list[Employee]] = {}
        next_emp_num = 1000

        for site in sites:
            depts = [Department(site_id=site.id, name=d, code=f"{site.code}-{d[:4].upper()}") for d in DEPARTMENTS]
            db.add_all(depts)
            db.flush()
            departments_by_site[site.id] = depts

            employees: list[Employee] = []
            for dept in depts:
                for title in JOB_TITLES.get(dept.name, ["General Staff"]):
                    emp = Employee(
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
                    next_emp_num += 1
                    employees.append(emp)
            db.add_all(employees)
            db.flush()
            employees_by_site[site.id] = employees

        budget_lines = []
        for site in sites:
            for dept in departments_by_site[site.id]:
                for cat, amt in CATEGORY_BUDGET.items():
                    line = BudgetLine(
                        site_id=site.id,
                        department_id=dept.id,
                        fiscal_year=date.today().year,
                        category=cat,
                        allocated=round(amt * rng.uniform(0.8, 1.2), 2),
                        spent=0.0,
                    )
                    budget_lines.append(line)
        db.add_all(budget_lines)
        db.flush()
        lines_by_site: dict[int, list[BudgetLine]] = {s.id: [l for l in budget_lines if l.site_id == s.id] for s in sites}

        # Expenses: 8 weeks of history so BI trends/anomalies have real data
        expenses = []
        exp_no = 1
        for site in sites:
            for i in range(90):
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

        # Requisitions with a mixed status history
        reqs = []
        req_no = 1
        for site in sites:
            for _ in range(12):
                dept = rng.choice(departments_by_site[site.id])
                requester = rng.choice(employees_by_site[site.id])
                cat = rng.choice(VENDOR_CATEGORIES)
                amount = round(rng.uniform(1_000, 60_000), 2)
                req = PurchaseRequisition(
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
                req_no += 1
                reqs.append(req)
        db.add_all(reqs)
        db.flush()

        # Purchase orders for approved requisitions
        pos = []
        po_no = 1
        vendors_flat = [v for vs in vendors_by_site.values() for v in vs]
        for req in reqs:
            if req.status in ("Ordered", "Received"):
                vendor = rng.choice([v for v in vendors_flat if v.site_id == req.site_id])
                po = PurchaseOrder(
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
                po_no += 1
                pos.append(po)
        db.add_all(pos)

        # Training records for employees
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

        # Capacity building activities (partnership progress tracking)
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
        db.flush()

        # Users: one per role at each site + shared admin/executive
        user_specs = [
            (ROLE_ADMIN, sites[0], "System Administrator"),
            (ROLE_EXECUTIVE, sites[0], "Executive Director"),
        ]
        for site in sites:
            user_specs.append((ROLE_HR, site, f"HR Officer {site.code}"))
            user_specs.append((ROLE_FINANCE, site, f"Finance Officer {site.code}"))
            user_specs.append((ROLE_APPROVER, site, f"Department Head {site.code}"))
            user_specs.append((ROLE_STAFF, site, f"Staff Member {site.code}"))

        role_map = {r.name: r for r in roles}
        slug = {
            ROLE_ADMIN: "admin",
            ROLE_EXECUTIVE: "executive",
            ROLE_HR: "hr",
            ROLE_FINANCE: "finance",
            ROLE_APPROVER: "depthead",
            ROLE_STAFF: "staff",
        }
        users = []
        for role_name, site, label in user_specs:
            email = f"{slug[role_name]}.{site.code.lower()}@airport360.com"
            users.append(
                User(
                    email=email,
                    full_name=label,
                    hashed_password=hash_password("Demo1234!"),
                    role_id=role_map[role_name].id,
                    site_id=site.id,
                    employee_id=rng.choice(employees_by_site[site.id]).id if employees_by_site.get(site.id) else None,
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
        db.add_all(users)
        db.flush()

        db.commit()
        print(f"Seeded {len(sites)} sites, {len(db.scalars(select(Employee)).all())} employees, {len(expenses)} expenses, {len(reqs)} requisitions.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
