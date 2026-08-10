from app.config import Settings


def test_turso_dashboard_url_is_normalized():
    s = Settings(database_url="libsql://airport360-chimwemwe.turso.io")
    assert s.database_url == "sqlite+libsql://airport360-chimwemwe.turso.io?secure=true"


def test_turso_url_with_query_is_kept():
    s = Settings(database_url="sqlite+libsql://airport360-chimwemwe.turso.io?secure=true")
    assert s.database_url == "sqlite+libsql://airport360-chimwemwe.turso.io?secure=true"


def test_local_sqlite_is_untouched():
    s = Settings(database_url="sqlite:///./airport360.db")
    assert s.database_url == "sqlite:///./airport360.db"
