from datetime import datetime, timezone
import json

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_initial_migration_builds_schema_from_empty_database(tmp_path):
    database = tmp_path / "persistence-phase1.sqlite"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database.as_posix()}")

    command.upgrade(config, "20260904_0001")

    legacy_engine = create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
    now = datetime(2026, 9, 1, 20, tzinfo=timezone.utc)
    stored_now = now.replace(tzinfo=None).isoformat(sep=" ")
    with legacy_engine.begin() as connection:
        connection.execute(text("insert into companies (company_id, canonical_name, created_at) values (:id, :name, :created)"), {"id": "legacy-company", "name": "Legacy", "created": stored_now})
        connection.execute(text("insert into instruments (instrument_id, company_id, ticker, exchange, currency, security_type, is_primary_listing, active) values (:id, :company, :ticker, :exchange, :currency, :security_type, :primary, :active)"), {"id": "legacy-instrument", "company": "legacy-company", "ticker": "LEG", "exchange": "NYSE", "currency": "USD", "security_type": "common_stock", "primary": True, "active": True})
        connection.execute(text("insert into price_snapshots (price_snapshot_id, instrument_id, timestamp, price, currency, source, price_type, created_at, payload) values (:id, :instrument, :timestamp, :price, :currency, :source, :price_type, :created, :payload)"), {"id": "legacy-price", "instrument": "legacy-instrument", "timestamp": stored_now, "price": 10, "currency": "USD", "source": "legacy", "price_type": "close", "created": stored_now, "payload": json.dumps({"price_snapshot_id": "legacy-price"})})
    legacy_engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        revision = connection.execute(text("select version_num from alembic_version")).scalar_one()
        legacy_basis = connection.execute(text("select price_basis, adjustment_version from price_snapshots where price_snapshot_id = 'legacy-price'" )).one()
    engine.dispose()

    assert revision == "20260904_0002"
    assert legacy_basis == ("raw", "")
    assert {
        "companies",
        "instruments",
        "analysis_snapshots",
        "metric_results",
        "price_snapshots",
        "benchmark_assignments",
        "performance_snapshots",
        "performance_horizons",
        "tracking_kpi_observations",
        "valuation_assumptions",
        "exit_multiple_evidence",
    } <= tables
