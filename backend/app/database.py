import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()

TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")


def build_sqlalchemy_url(raw_url: str) -> str:
    """Normalize a Turso/libSQL URL for SQLAlchemy.

    Turso's dashboard shows `libsql://host`; the sqlalchemy-libsql dialect is
    registered as `sqlite.libsql`, so the URL must use the `sqlite+libsql` scheme.
    TLS is implied for libsql://, but `?secure=true` makes it explicit (and is
    idempotent if already present).
    """
    url = raw_url.strip()
    if url.startswith("libsql://") and not url.startswith("sqlite+libsql://"):
        url = url.replace("libsql://", "sqlite+libsql://", 1)
    if url.startswith("sqlite+libsql://") and "?" not in url:
        url = f"{url}?secure=true"
    return url


if TURSO_DATABASE_URL:
    connect_args = {"auth_token": TURSO_AUTH_TOKEN} if TURSO_AUTH_TOKEN else {}
    # NullPool: Turso closes idle Hrana streams server-side, and libsql-experimental
    # PANICS (pyo3 Option::unwrap on None) when a pooled connection reuses a closed
    # stream. A fresh connection per request sidesteps that entirely (pool_pre_ping
    # does not help: the driver's ping runs against its local replica, not the remote).
    engine = create_engine(
        build_sqlalchemy_url(TURSO_DATABASE_URL),
        connect_args=connect_args,
        poolclass=NullPool,
    )
else:
    engine = create_engine(
        os.environ.get("DATABASE_URL", "sqlite:///./airport360.db"),
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    # Keeps ORM instances usable across the seed's frequent commits (avoids
    # hundreds of pointless re-selects against the remote Turso database).
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_column(table: str, column: str, col_type: str) -> None:
    """Idempotently add a column to an existing table.

    Base.metadata.create_all() only creates missing tables — it never alters
    tables that already exist. Pre-existing databases (e.g. the deployed Turso
    DB) therefore lack columns added to the models later. This runs at startup
    and issues a no-op-safe ``ALTER TABLE`` when the column is absent.
    """
    with engine.connect() as conn:
        try:
            existing = {col["name"] for col in inspect(conn).get_columns(table)}
        except Exception:
            existing = set()
        if column not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            conn.commit()
