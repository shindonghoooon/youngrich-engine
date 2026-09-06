"""Fixture-to-normalized-input adapter is test-only, never product acquisition."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select

from engine.persistence.models import Base, AnalysisSnapshotRow, CompanyRow, InstrumentRow, OnboardingRecordRow
from engine.persistence.repositories import AnalysisRepository
from engine.persistence.session import create_sqlite_engine, create_session_factory
from engine.stock_onboarding import OnboardingInput, StockOnboardingService
from engine.watchlist_registry import WatchlistRepository
from test_case2_golden_validation import build_input, load_fixture


def onboarding_input(ticker="IONQ"):
    data = load_fixture(ticker)
    golden = build_input(data)
    now = golden.as_of
    company_id, instrument_id = "company-" + ticker, "instrument-" + ticker
    return OnboardingInput.model_validate(dict(
        request_id=ticker + "-onboarding-validation-v1",
        company=dict(company_id=company_id, canonical_name=data["company_name"], created_at=now),
        instrument=dict(instrument_id=instrument_id, company_id=company_id, ticker=ticker, exchange="NASDAQ", currency="USD"),
        router=dict(profitable=False, recent_operating_loss=True), as_of=now, created_at=now,
        financial_currency="USD", financial_unit_scale=1000, usage="DEMO/VALIDATION",
        sources=[dict(source_reference_id=ticker + "-" + key, source_type="validation-fixture",
            reference=value["url"], available_at=value["available_at"]) for key, value in data["sources"].items()],
        case2=golden.quant, case2_current=golden.current, narrative=golden.narrative,
        commercial_evidence_exists=golden.commercial_evidence_exists,
        thesis_breaker_triggered=golden.thesis_breaker_triggered,
        valuation=dict(assumptions=golden.valuation_assumptions, evidence=golden.valuation_evidence,
            required_return=golden.required_return, asymmetry_type=golden.asymmetry_type,
            usage="DEMO/VALIDATION", approval_reference="fixture validation-only range; not operating approval",
            current_shares=data["market"]["shares_for_market_cap"],
            shares_period_end=data["current"]["period_end"], shares_available_at=golden.current.available_at,
            share_basis_version="fixture-reported-actual-common-shares",
            price_share_basis_verified=True),
        price=dict(price_snapshot_id=ticker + "-onboarding-price", ticker=ticker, company_id=company_id,
            timestamp=now, price=data["market"]["close"], currency="USD", source=data["sources"]["price"]["source"],
            provider_reference=data["sources"]["price"]["url"], price_type="close", price_basis="raw", created_at=now),
        price_instrument_id=instrument_id, price_session_date=now.date(), exchange_timezone="America/New_York",
    ))


@pytest.fixture
def onboarding_db(tmp_path):
    path = tmp_path / "onboarding.sqlite"
    engine = create_sqlite_engine(path)
    Base.metadata.create_all(engine)
    with create_session_factory(engine)() as session:
        yield session, path
    engine.dispose()


def test_ionq_end_to_end_and_idempotent(onboarding_db):
    session, path = onboarding_db
    request = onboarding_input()
    service = StockOnboardingService(session)
    result = service.analyze(request)
    assert result.analysis_status == "COMPLETE"
    assert result.watchlist_status is None
    assert result.valuation_status.value == "resolved"
    snapshot = AnalysisRepository(session).get_analysis_snapshot(result.analysis_snapshot_id)
    assert len([m for m in snapshot.quant.metrics if m.is_core]) == 6
    assert snapshot.investment_grade.model_version == "investment-grade-v1.1-safety"
    tracked = service.analyze(request, track=True)
    assert tracked.watchlist_status.value == "ACTIVE"
    assert service.analyze(request, track=True) == tracked
    for table in (CompanyRow, InstrumentRow, AnalysisSnapshotRow, OnboardingRecordRow):
        assert session.scalar(select(func.count()).select_from(table)) == 1
    session.expire_all()
    assert AnalysisRepository(session).get_analysis_snapshot(snapshot.snapshot_id) == snapshot


def test_missing_valuation_is_valid_u_and_trackable(onboarding_db):
    session, _ = onboarding_db
    request = onboarding_input().model_copy(update={"valuation": None})
    result = StockOnboardingService(session).analyze(request, track=True)
    assert result.analysis_status == "COMPLETE"
    assert result.investment_grade.value == "U"
    assert result.watchlist_status.value == "ACTIVE"
    assert "VALUATION_ASSUMPTIONS_UNAVAILABLE" in result.unresolved_reasons


def test_same_request_changed_content_rejected_and_new_request_appends(onboarding_db):
    session, _ = onboarding_db
    request = onboarding_input()
    service = StockOnboardingService(session)
    first = service.analyze(request)
    modified = request.model_copy(update={"valuation": None})
    with pytest.raises(ValueError, match="different input"):
        service.analyze(modified)
    second = service.analyze(modified.model_copy(update={"request_id": "new-analysis"}))
    assert first.analysis_snapshot_id != second.analysis_snapshot_id
    assert len(AnalysisRepository(session).list_analysis_snapshots(request.instrument.instrument_id)) == 2


@pytest.mark.parametrize("router,status", [
    ({"profitable": False}, "CASE_UNRESOLVED"),
    ({"profitable": False, "structurally_cyclical": True}, "BLOCKED_UNIMPLEMENTED_CASE"),
])
def test_unsupported_and_unresolved_routes(onboarding_db, router, status):
    session, _ = onboarding_db
    payload = onboarding_input().model_dump()
    payload.update(router=router, case2=None, case2_current=None, narrative=None, valuation=None)
    result = StockOnboardingService(session).analyze(OnboardingInput.model_validate(payload), track=True)
    assert result.case_status == status
    assert result.analysis_snapshot_id is None
    assert result.investment_grade is None  # no fabricated U without analysis
    assert result.watchlist_status.value == "ACTIVE"


@pytest.mark.parametrize("field", ["as_of", "price", "currency", "basis", "session", "source"])
def test_bad_temporal_and_price_inputs_fail(field):
    payload = onboarding_input().model_dump(mode="json")
    if field == "as_of":
        payload["as_of"] = "2024-01-01T00:00:00Z"
    elif field == "price":
        payload["price_instrument_id"] = "wrong-instrument"
    elif field == "currency":
        payload["price"]["currency"] = "KRW"
    elif field == "basis":
        payload["price"]["price_basis"] = "split_adjusted"
    elif field == "session":
        payload["price_session_date"] = "2026-08-31"
    else:
        payload["sources"][0]["available_at"] = "2030-01-01T00:00:00Z"
    with pytest.raises(ValueError):
        OnboardingInput.model_validate(payload)


def test_missing_basis_and_missing_price_are_safe_u(onboarding_db):
    session, _ = onboarding_db
    request = onboarding_input()
    request = request.model_copy(update={"valuation": request.valuation.model_copy(update={"price_share_basis_verified": False})})
    result = StockOnboardingService(session).analyze(request)
    assert result.investment_grade.value == "U"
    assert "SHARE_SPLIT_BASIS_UNRESOLVED" in result.unresolved_reasons


def test_no_ticker_or_fixture_dependency_in_product_source():
    source = Path("engine/stock_onboarding.py").read_text(encoding="utf-8")
    for forbidden in ('"IONQ"', '"STRL"', '"TEM"', '"LPTH"', 'tests/fixtures', 'load_fixture'):
        assert forbidden not in source


def test_registry_lifecycle_preserves_history(onboarding_db):
    session, _ = onboarding_db
    request = onboarding_input()
    result = StockOnboardingService(session).analyze(request, track=True)
    repo = WatchlistRepository(session)
    before = repo.get(request.instrument.instrument_id)
    assert repo.add(before.instrument_id, at=request.created_at) == before
    stopped = repo.deactivate(before.instrument_id, at=request.created_at + timedelta(days=1))
    assert stopped.status.value == "INACTIVE"
    assert repo.list_active_watchlist() == ()
    active = repo.add(before.instrument_id, at=request.created_at + timedelta(days=2))
    assert active.membership_id == before.membership_id
    assert active.created_at == before.created_at
    assert active.reference_analysis_snapshot_id == result.analysis_snapshot_id
    assert len(AnalysisRepository(session).list_analysis_snapshots(before.instrument_id)) == 1
