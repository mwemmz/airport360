def _make_requisition_payload(client, headers, dept_id=None, emp_id=None):
    if dept_id is None:
        depts = client.get("/v1/hr/departments", headers=headers).json()
        dept_id = depts[0]["id"]
    if emp_id is None:
        emps = client.get("/v1/hr/employees", headers=headers).json()
        emp_id = emps[0]["id"]
    return {
        "department_id": dept_id,
        "requested_by_employee_id": emp_id,
        "title": "Test IT equipment",
        "description": "Simulated requisition for tests",
        "category": "IT Equipment",
        "estimated_amount": 4500.0,
        "currency": "USD",
    }


def test_requisition_to_po_full_flow(client, ku_staff_headers, ku_hr_headers, ku_approver_headers, ku_finance_headers):
    payload = _make_requisition_payload(client, ku_hr_headers)
    resp = client.post("/v1/procurement/requisitions", json=payload, headers=ku_staff_headers)
    assert resp.status_code == 201
    req = resp.json()
    assert req["status"] == "Submitted"

    resp = client.post(f"/v1/procurement/requisitions/{req['id']}/approve", headers=ku_approver_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "Approved"
    assert resp.json()["approved_by"]

    vendors = client.get("/v1/procurement/vendors", headers=ku_finance_headers).json()
    resp = client.post(
        "/v1/procurement/purchase-orders",
        json={"requisition_id": req["id"], "vendor_id": vendors[0]["id"], "total_amount": 4500.0},
        headers=ku_finance_headers,
    )
    assert resp.status_code == 201
    po = resp.json()
    assert po["status"] == "Issued"

    resp = client.post(f"/v1/procurement/purchase-orders/{po['id']}/receive", headers=ku_finance_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "Received"

    # BI reflects the requisition
    resp = client.get("/v1/bi/overview", headers=ku_finance_headers)
    assert resp.status_code == 200
    assert resp.json()["total_requisitions"] >= 1


def test_staff_cannot_approve_own_requisition(client, ku_staff_headers, ku_hr_headers):
    payload = _make_requisition_payload(client, ku_hr_headers)
    req = client.post("/v1/procurement/requisitions", json=payload, headers=ku_staff_headers).json()
    resp = client.post(f"/v1/procurement/requisitions/{req['id']}/approve", headers=ku_staff_headers)
    assert resp.status_code == 403


def test_finance_cannot_create_employee(client, ku_finance_headers):
    depts = client.get("/v1/hr/departments", headers=ku_finance_headers).json()
    resp = client.post(
        "/v1/hr/employees",
        params={
            "employee_number": "EMP-TEST-1",
            "first_name": "A",
            "last_name": "B",
            "email": "a.b@test.local",
            "department_id": depts[0]["id"],
            "job_title": "Test",
            "hire_date": "2024-01-01",
        },
        headers=ku_finance_headers,
    )
    assert resp.status_code == 403


def test_unauthenticated_rejected(client):
    resp = client.get("/v1/procurement/requisitions")
    assert resp.status_code == 401
