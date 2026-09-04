"""SQLAlchemy engine/session construction without global database state."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_sqlite_engine(path: str | Path = ":memory:") -> Engine:
    if str(path) == ":memory:":
        url = "sqlite+pysqlite:///:memory:"
    else:
        url = f"sqlite+pysqlite:///{Path(path).as_posix()}"
    engine = create_engine(url, future=True)
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
