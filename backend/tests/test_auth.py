def test_login_success(client):
    resp = client.post("/v1/auth/login", json={"email": "hr.ku@airport360.com", "password": "Demo1234!"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["role"]["name"] == "HR Officer"
    assert body["user"]["site_id"] == 1


def test_login_wrong_password(client):
    resp = client.post("/v1/auth/login", json={"email": "hr.ku@airport360.com", "password": "wrong"})
    assert resp.status_code == 401


def test_me_returns_identity(client, ku_hr_headers):
    resp = client.get("/v1/auth/me", headers=ku_hr_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "hr.ku@airport360.com"


def test_me_requires_token(client):
    resp = client.get("/v1/auth/me")
    assert resp.status_code == 401
