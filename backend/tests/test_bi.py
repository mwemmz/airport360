def test_bi_overview_has_no_hardcoded_numbers(client, ku_finance_headers):
    resp = client.get("/v1/bi/overview", headers=ku_finance_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["headcount"] >= 1
    assert body["total_spend"] > 0
    assert body["total_budget"] > 0
    assert 0 <= body["budget_utilization"] <= 100


def test_bi_anomaly_flags_carry_the_rule(client, ku_finance_headers):
    resp = client.get("/v1/bi/anomalies", headers=ku_finance_headers)
    assert resp.status_code == 200
    flags = resp.json()
    for flag in flags:
        assert "rule" in flag["flag"]
        assert "threshold" in flag["flag"]
        assert flag["flag"]["is_anomaly"] is True


def test_bi_spend_trend_by_site(client, exec_headers):
    resp = client.get("/v1/bi/spend-by-site", headers=exec_headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2


def test_capacity_building_overview(client, ku_hr_headers):
    resp = client.get("/v1/bi/capacity-building", headers=ku_hr_headers)
    assert resp.status_code == 200
    assert "by_status" in resp.json()
    assert "by_module" in resp.json()


def test_audit_log_tracks_flow(client, admin_headers, ku_hr_headers, ku_staff_headers, ku_approver_headers):
    payload = {
        "department_id": client.get("/v1/hr/departments", headers=ku_hr_headers).json()[0]["id"],
        "requested_by_employee_id": client.get("/v1/hr/employees", headers=ku_hr_headers).json()[0]["id"],
        "title": "Auditable requisition",
        "category": "Consumables",
        "estimated_amount": 500,
    }
    req = client.post("/v1/procurement/requisitions", json=payload, headers=ku_staff_headers).json()
    client.post(f"/v1/procurement/requisitions/{req['id']}/approve", headers=ku_approver_headers)

    logs = client.get("/v1/audit", headers=admin_headers).json()
    actions = [l["action"] for l in logs]
    assert "create_requisition" in actions
    assert "approve_requisition" in actions
