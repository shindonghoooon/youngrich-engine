from datetime import timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from engine.persistence.models import Base, InstrumentRow, AnalysisSnapshotRow, OnboardingRecordRow
from engine.persistence.repositories import AnalysisRepository, IdentityRepository, ThesisRepository
from engine.persistence.session import create_sqlite_engine, create_session_factory
from engine.read_only_watchlist import load_watchlist, WatchlistItemState
from engine.stock_onboarding import OnboardingInput, StockOnboardingService
from engine.watchlist_registry import WatchlistRepository
from research.watchlist import migrate
from test_stock_onboarding import onboarding_input, onboarding_db
from test_read_only_watchlist import stored_watchlist, _run_app, _app_text


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ionq_registry_drives_ui_without_network_or_writes(onboarding_db, monkeypatch):
    session, path = onboarding_db
    request = onboarding_input()
    result = StockOnboardingService(session).analyze(request, track=True)
    def forbidden(*args, **kwargs):
        raise AssertionError("UI must not call onboarding or acquisition")
    monkeypatch.setattr(StockOnboardingService, "analyze", forbidden)
    before = digest(path)
    view = load_watchlist(path)
    assert [item.ticker for item in view.items] == ["IONQ"]
    assert view.items[0].evaluation.investment_grade_result.final_grade == result.investment_grade
    assert view.items[0].evaluation.is_initial_analysis
    from app.read_only_watchlist import DB_ENV, ARTIFACT_ENV
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv(DB_ENV, str(path))
    monkeypatch.delenv(ARTIFACT_ENV, raising=False)
    app = AppTest.from_file(Path.cwd() / "app/read_only_watchlist.py").run()
    assert not app.exception
    assert "IONQ" in _app_text(app)
    assert "검증용 가정" in _app_text(app)
    assert "저장된 최초 분석" in _app_text(app)
    app.button[0].click().run()
    assert not app.exception
    assert digest(path) == before


def test_existing_three_plus_ionq_and_deactivation(stored_watchlist):
    path, artifacts = stored_watchlist
    original = load_watchlist(path, artifacts)
    before_artifacts = digest(artifacts)
    engine = create_sqlite_engine(path)
    with create_session_factory(engine)() as session:
        request = onboarding_input()
        StockOnboardingService(session).analyze(request, track=True)
        four = load_watchlist(path, artifacts)
        assert {i.ticker for i in four.items} == {"STRL", "TEM", "LPTH", "IONQ"}
        for item in original.items:
            assert four.item_for(item.ticker) == item
        WatchlistRepository(session).deactivate(request.instrument.instrument_id, at=request.created_at + timedelta(days=1))
        assert len(load_watchlist(path, artifacts).items) == 3
        assert AnalysisRepository(session).get_latest_analysis_snapshot(request.instrument.instrument_id)
    engine.dispose()
    assert digest(artifacts) == before_artifacts


def test_same_ticker_distinct_instruments_and_rename_safe(onboarding_db):
    session, path = onboarding_db
    request = onboarding_input()
    service = StockOnboardingService(session)
    service.analyze(request, track=True)
    other = request.instrument.model_copy(update={"instrument_id": "instrument-other", "exchange": "OTHER"})
    IdentityRepository(session).add_instrument(other)
    WatchlistRepository(session).add(other.instrument_id, at=request.created_at)
    view = load_watchlist(path)
    assert len(view.items) == 2
    with pytest.raises(ValueError, match="ambiguous"):
        view.item_for("IONQ")
    assert next(i for i in view.items if i.instrument_id == other.instrument_id).state == WatchlistItemState.MISSING_ANALYSIS
    row = session.get(InstrumentRow, request.instrument.instrument_id)
    row.ticker = "RENAMED"
    session.commit()
    renamed = load_watchlist(path).item_for("RENAMED")
    assert renamed.reference_analysis.ticker == "IONQ"
    assert renamed.evaluation.ticker == "IONQ"


def test_stored_u_without_price_is_not_missing_analysis(onboarding_db, monkeypatch):
    session, path = onboarding_db
    request = onboarding_input().model_copy(update={"price": None, "price_session_date": None, "price_instrument_id": None})
    result = StockOnboardingService(session).analyze(request, track=True)
    view = load_watchlist(path)
    assert view.items[0].state == WatchlistItemState.READY
    assert view.items[0].price_snapshot is None
    assert result.investment_grade.value == "U"
    from app.read_only_watchlist import DB_ENV, ARTIFACT_ENV
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv(DB_ENV, str(path))
    monkeypatch.delenv(ARTIFACT_ENV, raising=False)
    app = AppTest.from_file(Path.cwd() / "app/read_only_watchlist.py").run()
    assert not app.exception
    assert "저장된 가격 평가 없음" in _app_text(app)
    assert "판단 보류" in _app_text(app)


def test_legacy_analysis_without_price_evaluation_is_data_state(stored_watchlist):
    path, _ = stored_watchlist
    view = load_watchlist(path)
    assert all(item.state == WatchlistItemState.MISSING_EVALUATION for item in view.items)
    assert all(item.evaluation is None for item in view.items)


def test_explicit_cli_migration_onboarding_registration_and_reload(tmp_path):
    database = tmp_path / "cli.sqlite"
    artifact = tmp_path / "normalized-input.json"
    artifact.write_text(onboarding_input().model_dump_json(), encoding="utf-8")
    def run(module, *args):
        result = subprocess.run([sys.executable, "-B", "-m", module, *args, "--db", str(database)],
            capture_output=True, text=True, encoding="utf-8", check=True)
        return json.loads(result.stdout)
    assert run("research.watchlist", "migrate")["status"] == "COMPLETE"
    first = run("research.stock_onboarding", "analyze", "--input", str(artifact))
    assert first["watchlist_status"] is None
    assert run("research.watchlist", "list") == []
    tracked = run("research.stock_onboarding", "analyze", "--input", str(artifact), "--track")
    assert tracked["watchlist_status"] == "ACTIVE"
    active = run("research.watchlist", "list")
    assert active[0]["latest_analysis"]["snapshot_id"] == first["analysis_snapshot_id"]
    assert len(load_watchlist(database).items) == 1
    run("research.watchlist", "deactivate", "--instrument-id", "instrument-IONQ")
    assert run("research.watchlist", "list") == []


def test_migration_preserves_existing_unstamped_payloads(tmp_path):
    database = tmp_path / "old.sqlite"
    engine = create_sqlite_engine(database)
    tables = [t for t in Base.metadata.sorted_tables if t.name not in {"watchlist_memberships", "onboarding_records"}]
    Base.metadata.create_all(engine, tables=tables)
    from engine.limited_operating import LimitedOperatingService
    with create_session_factory(engine)() as session:
        LimitedOperatingService(session, repo_root=Path.cwd(), artifact_path=tmp_path / "absent.jsonl").seed_demo()
        before = session.execute(select(AnalysisSnapshotRow.snapshot_id, AnalysisSnapshotRow.payload)).all()
    engine.dispose()
    migrate(database)
    migrate(database)
    engine = create_sqlite_engine(database)
    with create_session_factory(engine)() as session:
        assert session.execute(select(AnalysisSnapshotRow.snapshot_id, AnalysisSnapshotRow.payload)).all() == before
        assert session.execute(text("select version_num from alembic_version")).scalar_one() == "20260906_0003"
        assert WatchlistRepository(session).list_active_watchlist() == ()
    engine.dispose()


def test_postgresql_compile_additive_tables():
    for name in ("watchlist_memberships", "onboarding_records"):
        sql = str(CreateTable(Base.metadata.tables[name]).compile(dialect=postgresql.dialect()))
        assert "CREATE TABLE" in sql
        assert "FOREIGN KEY" in sql
