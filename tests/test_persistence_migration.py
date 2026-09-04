from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_initial_migration_builds_schema_from_empty_database(tmp_path):
    database = tmp_path / "persistence-phase1.sqlite"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database.as_posix()}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        revision = connection.execute(text("select version_num from alembic_version")).scalar_one()
    engine.dispose()

    assert revision == "20260904_0001"
    assert {
        "companies",
        "instruments",
        "analysis_snapshots",
        "metric_results",
        "price_snapshots",
        "tracking_kpi_observations",
        "valuation_assumptions",
        "exit_multiple_evidence",
    } <= tables
