from app.database import build_sqlalchemy_url


def test_turso_dashboard_url_is_normalized():
    assert build_sqlalchemy_url("libsql://airport360-chimwemwe.turso.io") == (
        "sqlite+libsql://airport360-chimwemwe.turso.io?secure=true"
    )


def test_turso_url_with_query_is_kept():
    assert build_sqlalchemy_url("sqlite+libsql://airport360-chimwemwe.turso.io?secure=true") == (
        "sqlite+libsql://airport360-chimwemwe.turso.io?secure=true"
    )


def test_whitespace_is_stripped():
    assert build_sqlalchemy_url("  libsql://airport360-chimwemwe.turso.io  ") == (
        "sqlite+libsql://airport360-chimwemwe.turso.io?secure=true"
    )


def test_local_sqlite_is_untouched():
    assert build_sqlalchemy_url("sqlite:///./airport360.db") == "sqlite:///./airport360.db"


def test_engine_is_sqlite_in_test_env():
    # conftest.py sets DATABASE_URL to a temp sqlite file before import.
    from app.database import engine

    assert engine.url.get_backend_name() == "sqlite"
