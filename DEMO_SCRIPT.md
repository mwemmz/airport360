# Airport360 Demo Script

**MoU basis:** ZACL–Copperbelt University Strategic MoU (signed 12 May 2026, ZACL Head Office, KKIA) — locally-driven, phased ERP implementation beginning with **Human Resources, Procurement, Finance, Capacity Building and Business Intelligence**, with focus on **innovation, automation, business intelligence, artificial intelligence, institutional capacity building and systems integration**.

**URL:** https://airport360-frontend.onrender.com
**Backend:** https://airport360-api.onrender.com

| Role | Email | Password |
|---|---|---|
| System Administrator | `admin.ku@airport360.com` | `Demo1234!` |
| Executive Director | `executive.ku@airport360.com` | `Demo1234!` |
| HR Officer | `hr.ku@airport360.com` | `Demo1234!` |
| Finance Officer | `finance.ku@airport360.com` | `Demo1234!` |
| Operations Manager | `ops.ku@airport360.com` | `Demo1234!` |
| Department Head (Approver) | `approver.ku@airport360.com` | `Demo1234!` |

---

## 0. Opening (1–2 min)

> "Good day. In May this year, ZACL signed a strategic MoU with Copperbelt University to drive the Corporation's digital transformation through a **locally developed, phased ERP system**. The partnership focuses on innovation, automation, business intelligence, artificial intelligence, institutional capacity building and systems integration.
>
> This is Airport360 — our working implementation of that vision. It begins exactly where the MoU says the ERP begins: **Human Resources, Procurement, Finance, Capacity Building and Business Intelligence**, and then extends into the broader operations and AI-driven tools. All data you will see today is simulated for demonstration; every number is computed live from the database — nothing is hardcoded."

---

## 1. Login & First Impressions (1 min)

- Open the frontend URL.
- Log in as **System Administrator** (`admin.ku@airport360.com` / `Demo1234!`).
- Point out: modern dashboard, sidebar navigation grouped by function, "Site KU — Kuomboka International Airport" pill in the top-left (this becomes the site switcher later).

> **Narrator cue:** "One login, one platform — every module behind us is driven by the same database, which is the whole point of an ERP."

---

## 2. Human Resources — first MoU phase module (3 min)

Navigate to **Human Resources** (sidebar → Human Resources).

- **Employees table** — 18+ employees per site with employee numbers, job titles, departments, employment status.
- **Add employee** (button in card) — create an employee live, it appears in the table immediately (no refresh).
- **Training records** — now grouped per employee: shows *who has which course*, provider, status, and ✓ certified badge. Summary counters: total records, employees trained.
- **Departments** — used across Finance and Procurement.

> **Narrator cue:** "The MoU names HR as the first core ERP area. Here we see the full employee lifecycle — records, departments, and per-employee training and certification tracking, because capacity building is one of the partnership's explicit goals."

---

## 3. Procurement (3 min)

Navigate to **Procurement**.

- **Requisitions** — status workflow: Submitted → Approved → Purchase Order → Received.
- **Create a requisition** live, then **Approve** it as the workflow.
- **Vendors** list.
- **Purchase Orders** table.

> **Narrator cue:** "Procurement is the second MoU phase area. Every step of the requisition-to-payment workflow is tracked and audited — and, as we'll see later, it feeds directly into Finance and Business Intelligence with no re-keying."

---

## 4. Finance (3 min)

Navigate to **Finance**.

- **Budgets** vs actual spend per department.
- **Expenses** — categorized, date-stamped, linked to departments.
- **Add an expense** live.

> **Narrator cue:** "Finance is the third MoU phase area. Internal budgets, expense capture, and category-level control — no payment processing, deliberately kept out of PCI scope. Everything here is visible to Finance Officers and Executive."

---

## 5. Capacity Building — the MoU's institutional capacity pillar (2 min)

Navigate to **Capacity Building**.

- **Activities** table — workshops, project work, certifications, internships mapped to platform modules (HR, Procurement, Finance, BI, Platform Core).
- **Record activity** live.

> **Narrator cue:** "The MoU is not just about software — it's about building Zambian institutional capacity. This module tracks who worked on which part of the platform, participation, and training program status. It is the living record of the CBU–ZACL partnership itself."

---

## 6. Business Intelligence — the fourth MoU phase area (3 min)

Navigate to **Dashboard**.

- **KPI stat cards** — revenue categories, headcount, budgets, training.
- **Spend trend chart** (60 days) — gradient area chart.
- **Spend by category** — bar chart.
- **Budget vs actual** — comparison.
- **Capacity building overview** — donut/pie chart.
- **Anomalies** — computed spend anomalies.

> **Narrator cue:** "Business Intelligence is the fifth MoU phase area. One executive screen summarises the entire ERP — HR, procurement, finance, capacity building — so decision-makers get data-driven insight instead of spreadsheets. These charts are generated live from the same data the modules feed."

---

## 7. Operations & Automation (4 min)

Navigate to **Command Center** (sidebar → Command Center).

- **Operational KPIs** — passengers, queue length, wait time, incidents, maintenance, baggage exceptions, cargo in processing.
- **Risk level** — computed from a documented rule (critical incidents × 2 + congestion + delayed bags + cargo delays + high-priority maintenance), not hardcoded.
- **Event timeline** — alerts, incidents, flights, predictions merged into one live feed.

> **Narrator cue:** "Beyond the core ERP, the MoU calls for automation. This is the operational layer — a single command center for the whole airport."

### 7a. Queue predictions (automation) — 2 min

Navigate to **Queues & Predictions**.

- **Run a prediction** — pick queue type and horizon, click Predict.
- Shows predicted length, congestion level, model name/version, trained live on queue history.

> **Narrator cue:** "A real forecasting model — trained on the site's queue history each time you ask. This is the 'automation and AI' the MoU explicitly calls for."

### 7b. Computer Vision (privacy-preserving AI) — 2 min

Navigate to **Computer Vision**.

- Upload a CCTV-style video clip (or show the interface).
- Result: density level, avg/peak people, estimated queue length, occupancy, frames processed.
- **Emphasize the privacy tag:** "HOG person detector — aggregate metrics only, frames never stored, no facial recognition."

> **Narrator cue:** "AI for crowd and queue analysis that respects privacy — aggregate metrics only, frames processed in memory and never stored, no facial recognition. This is AI built to airport security standards."

---

## 8. AI Assistant (2 min)

Navigate to **AI Assistant**.

- Ask: **"Predict the security queue"** or **"What is the current operational status?"**
- Show the answer card split into **Facts**, **Predictions**, **Recommendations** with the tagging footer.
- Show the **recommendations sidebar** with `triggered_by` chips.

> **Narrator cue:** "A rule-based assistant that answers from live platform data — not canned responses. Facts, predictions and recommendations are computed from what we've just seen in HR, procurement, finance and operations."

---

## 9. Systems Integration & Multi-Site (3 min)

Navigate back to any data page, then:

- In the top-left site pill, **click the site dropdown** and switch from **KU (Kuomboka International)** to **NM (Namwala Regional)**.
- Show that the data (employees, flights, queues) now reflects Site NM — the platform is one system across the whole ZACL airport network.

> **Narrator cue:** "The MoU is a corporation-wide ERP. Airport360 is multi-site from day one — one platform, every ZACL airport, with role-based and site-based access control. Executives can switch between sites; officers see only their own."

### 9a. Administration & governance (2 min)

Navigate to **Administration** (Administrator only).

- **Users** — manage roles and sites; toggle a user active/inactive.
- **Sites** — the network of airports.
- **Audit log** — every action recorded (who, what, when).

> **Narrator cue:** "Full governance — audit logging on every mutation, RBAC roles, and site management. This is what makes it a trustworthy enterprise system."

---

## 10. Supporting modules (1 min, optional)

If time allows, flash through: **Flights, Baggage, Incidents, Maintenance, Cargo, Alerts, Complaints, Booking Marketplace, Passenger Portal** — each is a business-critical function the ERP "expands to" after the core phases, per the MoU.

> **Narrator cue:** "These are the 'expanding to other business-critical functions' from the release — flights, baggage, incidents, maintenance, cargo, alerts, complaints, bookings and the passenger portal."

---

## 11. Closing (1 min)

> "To recap: this is a **locally developed ERP** that starts exactly where the MoU starts — **HR, Procurement, Finance, Capacity Building and Business Intelligence** — and layers on **automation, AI, business intelligence, and systems integration** across the whole airport network. It is the CBU–ZACL partnership made real, and it's ready to grow with the Corporation's phasing plan.
>
> **One honest note:** today's data is simulated and this is a working prototype, not yet wired into ZACL's existing check-in, immigration or revenue systems. What it proves is that the ERP the MoU describes is buildable, locally, and end-to-end."

---

## Demo tips

- Run the demo in **two browser windows** (Admin + an HR/Finance login) to show role-based access quickly.
- Pre-upload a short video clip for the Computer Vision step so it runs instantly.
- Practice the **site switch** (step 9) — it's the most impressive moment for executives.
- Keep narration tied to the MoU release language: *locally driven, phased, core ERP first (HR, Procurement, Finance, Capacity Building, BI), automation, AI, BI, capacity building, systems integration*.
