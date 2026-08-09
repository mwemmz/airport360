"""Cross-site isolation is a Phase 1 requirement. These tests assert that no query
path returns another site's data and that every site-scoped request resolves to
exactly the caller's own site."""


def test_hr_cannot_read_other_site_employees(client, ku_hr_headers, nm_hr_headers):
    resp = client.get("/v1/hr/employees", params={"site_id": 2}, headers=ku_hr_headers)
    assert resp.status_code == 403


def test_finance_cannot_read_other_site_expenses(client, ku_finance_headers):
    resp = client.get("/v1/finance/expenses", params={"site_id": 2}, headers=ku_finance_headers)
    assert resp.status_code == 403


def test_approver_cannot_approve_other_site_requisition(client, ku_approver_headers, nm_hr_headers):
    # Find a requisition belonging to site 2 (NM)
    nm_reqs = client.get("/v1/procurement/requisitions", headers=nm_hr_headers).json()
    other_site_req = [r for r in nm_reqs if r["site_id"] == 2]
    if not other_site_req:
        return
    resp = client.post(
        f"/v1/procurement/requisitions/{other_site_req[0]['id']}/approve", headers=ku_approver_headers
    )
    assert resp.status_code == 403


def test_default_site_resolves_to_caller_site(client, ku_hr_headers, nm_hr_headers):
    ku_emps = client.get("/v1/hr/employees", headers=ku_hr_headers).json()
    nm_emps = client.get("/v1/hr/employees", headers=nm_hr_headers).json()
    assert ku_emps and nm_emps
    assert {e["site_id"] for e in ku_emps} == {1}
    assert {e["site_id"] for e in nm_emps} == {2}


def test_admin_can_read_cross_site(client, admin_headers):
    resp = client.get("/v1/hr/employees", params={"site_id": 2}, headers=admin_headers)
    assert resp.status_code == 200
    assert all(e["site_id"] == 2 for e in resp.json())


def test_executive_can_read_cross_site_bi(client, exec_headers):
    resp = client.get("/v1/bi/spend-by-site", headers=exec_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2
