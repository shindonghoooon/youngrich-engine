"""Explicit local registry commands. No prices, analysis or UI-side writes."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from engine.persistence.repositories import AnalysisRepository
from engine.persistence.session import create_session_factory, create_sqlite_engine
from engine.watchlist_registry import WatchlistRepository


def migrate(database: Path) -> None:
    """Explicitly migrate an existing DB, or initialize a requested empty DB.

    Old limited-operating databases used create_all without an Alembic stamp. Only
    adopt a complete, structurally compatible v0002 schema, never recreate it.
    """
    root = Path(__file__).resolve().parents[1]
    database = database.resolve()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", "sqlite+pysqlite:///" + database.as_posix())
    engine = create_sqlite_engine(database)
    try:
        schema = inspect(engine)
        tables = set(schema.get_table_names())
        if tables and "alembic_version" not in tables:
            from engine.persistence.models import Base
            legacy = {t.name: t for t in Base.metadata.sorted_tables
                      if t.name not in {"watchlist_memberships", "onboarding_records"}}
            if not set(legacy).issubset(tables):
                raise ValueError("unversioned DB is not a complete v0002 schema; manual migration review required")
            for name, table in legacy.items():
                actual = {c["name"] for c in schema.get_columns(name)}
                if not {c.name for c in table.columns}.issubset(actual):
                    raise ValueError("unversioned DB columns differ from v0002; manual migration review required")
            if tables & {"watchlist_memberships", "onboarding_records"}:
                raise ValueError("unstamped partial registry schema requires manual review")
            with engine.connect() as connection:
                differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
            if any(change[0] != "add_table" or change[1].name not in
                   {"watchlist_memberships", "onboarding_records"} for change in differences):
                raise ValueError("unversioned DB constraints/types differ from v0002; manual review required")
            command.stamp(config, "20260904_0002")
        command.upgrade(config, "head")
    finally:
        engine.dispose()


def existing_engine(database: Path):
    if not database.is_file():
        raise ValueError("database does not exist; run explicit watchlist migrate first")
    engine = create_sqlite_engine(database)
    if not {"watchlist_memberships", "onboarding_records"}.issubset(inspect(engine).get_table_names()):
        engine.dispose()
        raise ValueError("REGISTRY_MIGRATION_REQUIRED: run explicit watchlist migrate")
    return engine


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("migrate", "add", "list", "deactivate", "register-existing-watchlist"))
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--instrument-id", action="append", default=[])
    parser.add_argument("--reference-analysis-id")
    parser.add_argument("--at", type=datetime.fromisoformat)
    args = parser.parse_args(argv)
    try:
        if args.command == "migrate":
            migrate(args.db)
            print(json.dumps({"migration": "20260906_0003", "status": "COMPLETE"}))
            return
        engine = existing_engine(args.db)
        try:
            with create_session_factory(engine)() as session:
                repo = WatchlistRepository(session)
                at = args.at or datetime.now(timezone.utc)
                if args.command == "list":
                    values = repo.list_active_watchlist()
                else:
                    if not args.instrument_id:
                        raise ValueError("explicit --instrument-id is required; never register all instruments implicitly")
                    values = []
                    for instrument_id in args.instrument_id:
                        if args.command == "deactivate":
                            values.append(repo.deactivate(instrument_id, at=at))
                        else:
                            ref = args.reference_analysis_id
                            if args.command == "register-existing-watchlist":
                                latest = AnalysisRepository(session).get_latest_analysis_snapshot(instrument_id)
                                ref = latest.snapshot_id if latest else None
                            values.append(repo.add(instrument_id, at=at, reference_analysis_snapshot_id=ref,
                                registration_source=args.command))
                print(json.dumps([v.model_dump(mode="json") for v in values], ensure_ascii=False))
        finally:
            engine.dispose()
    except ValueError as error:
        parser.exit(2, json.dumps({"status": "INVALID_INPUT", "reason": str(error)}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
