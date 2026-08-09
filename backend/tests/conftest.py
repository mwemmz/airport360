import os
import tempfile

import pytest

# Point at an isolated test database BEFORE importing the app package.
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.mkdtemp(), 'test_airport360.db')}"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db_setup():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.close()


def _seed():
    from app.seed import seed_all

    seed_all()


@pytest.fixture(scope="session")
def seeded():
    _seed()
    return True


@pytest.fixture()
def client(seeded):
    return TestClient(app)


def login(client, email, password="Demo1234!"):
    resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture()
def auth_headers(client):
    def _headers(email):
        token = login(client, email)["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture()
def admin_headers(auth_headers):
    return auth_headers("admin.ku@airport360.com")


@pytest.fixture()
def exec_headers(auth_headers):
    return auth_headers("executive.ku@airport360.com")


@pytest.fixture()
def ku_hr_headers(auth_headers):
    return auth_headers("hr.ku@airport360.com")


@pytest.fixture()
def ku_finance_headers(auth_headers):
    return auth_headers("finance.ku@airport360.com")


@pytest.fixture()
def ku_approver_headers(auth_headers):
    return auth_headers("depthead.ku@airport360.com")


@pytest.fixture()
def ku_staff_headers(auth_headers):
    return auth_headers("staff.ku@airport360.com")


@pytest.fixture()
def ku_ops_headers(auth_headers):
    return auth_headers("ops.ku@airport360.com")


@pytest.fixture()
def nm_ops_headers(auth_headers):
    return auth_headers("ops.nm@airport360.com")


@pytest.fixture()
def ku_passenger_headers(auth_headers):
    return auth_headers("passenger.ku@airport360.com")


@pytest.fixture()
def nm_hr_headers(auth_headers):
    return auth_headers("hr.nm@airport360.com")
