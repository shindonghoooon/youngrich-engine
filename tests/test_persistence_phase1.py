from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from engine.models import Grade, Trend
from engine.persistence.models import (
    AnalysisSnapshotRow,
    Base,
    ExitMultipleEvidenceRow,
    ImmutableRecordError,
    MetricResultRow,
    ThesisStatusSnapshotRow,
)
from engine.persistence.repositories import (
    AnalysisRepository,
    IdentityRepository,
    PriceRepository,
    SourceRepository,
    ThesisRepository,
    ValuationRepository,
)
from engine.persistence.schemas import Company, Instrument, SourceReference
from engine.persistence.session import create_session_factory, create_sqlite_engine
from engine.tracking_models import (
    AdjustmentType,
    AnalysisCase,
    AnalysisSnapshot,
    AsymmetryType,
    AssumptionRange,
    CurrentTrendSignal,
    CurrentTrendSnapshot,
    DirectionState,
    ExitMultipleAssumption,
    ExitMultipleBand,
    ExitMultipleEvidenceSource,
    ExpectationGap,
    InvestmentGrade,
    InvestmentGradeAdjustment,
    InvestmentGradeSnapshot,
    InvestmentGradeTrigger,
    KPIDirection,
    MetricResult,
    NarrativeAssessment,
    NarrativeGate,
    NarrativeSnapshot,
    NarrativeState,
    PriceSnapshot,
    PriceType,
    QuantSnapshot,
    ResolutionState,
    TerminalStage,
    ThesisDefinition,
    ThesisStatus,
    ThesisStatusSnapshot,
    TrackingKPIDefinition,
    TrackingKPIObservation,
    TrendFlag,
    ValuationAssumptionSet,
    ValuationConfidence,
    ValuationMetric,
    ValuationOutput,
    ValuationSnapshot,
)


UTC = timezone.utc
AS_OF = datetime(2026, 9, 1, 20, tzinfo=UTC)
PERIOD_END = date(2026, 6, 30)


@pytest.fixture
def session():
    engine = create_sqlite_engine()
    Base.metadata.create_all(engine)
    with create_session_factory(engine)() as db_session:
        yield db_session


def seed_identity(session):
    repo = IdentityRepository(session)
    company = Company(company_id="company-test", canonical_name="Test Company", country="US", created_at=AS_OF)
    instrument = Instrument(instrument_id="instrument-test", company_id=company.company_id, ticker="TEST", exchange="NASDAQ", currency="USD")
    repo.add_company(company)
    repo.add_instrument(instrument)
    return company, instrument


def assumptions(version=1):
    return ValuationAssumptionSet(
        assumption_set_id="test-assumptions",
        version=version,
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        horizon_years=3,
        terminal_stage=TerminalStage.MATURE,
        terminal_stage_rationale="frozen reverse valuation fixture",
        terminal_stage_confidence=ValuationConfidence.MEDIUM,
        primary_metric=ValuationMetric.PE,
        exit_multiples=tuple(
            ExitMultipleAssumption(
                band=band,
                metric_type=ValuationMetric.PE,
                value=value,
                evidence_type=ExitMultipleEvidenceSource.COMPANY_HISTORY,
                source_reference=f"official history {band.value}",
                as_of=AS_OF,
                rationale="historical reference range",
            )
            for band, value in zip(ExitMultipleBand, (12.0, 16.0, 20.0), strict=True)
        ),
        plausible_growth_range=AssumptionRange(low=0.10, high=0.20),
    )


def full_analysis(prefix="a1", *, assumption_version=1, thesis_status=ThesisStatus.CONFIRMING, base_value=120.0):
    quant = QuantSnapshot(
        snapshot_id=f"{prefix}-quant",
        ticker="TEST",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        model_version="case1-v1-frozen",
        metrics=(
            MetricResult(name="revenue_growth", state=ResolutionState.RESOLVED, value=0.20, unit="ratio", grade=Grade.A, trend=Trend.ACCELERATING, weight=0.5),
            MetricResult(name="capital_efficiency", state=ResolutionState.UNRESOLVED, value=None, grade=None, weight=0.5, note="official input unavailable"),
        ),
        state=ResolutionState.RESOLVED,
        score=4.0,
        uncapped_grade=Grade.A,
        grade=Grade.A,
        coverage=0.5,
        provisional=True,
        period_end=PERIOD_END,
        available_at=AS_OF - timedelta(hours=2),
        as_of=AS_OF,
    )
    current = CurrentTrendSnapshot(
        snapshot_id=f"{prefix}-current",
        ticker="TEST",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        model_version="case1-current-v1-frozen",
        signals=(CurrentTrendSignal(name="revenue", state=DirectionState.POSITIVE, observation="same-period acceleration"),),
        overall=DirectionState.POSITIVE,
        flags=frozenset({TrendFlag.COMMERCIAL_INFLECTION, TrendFlag.FUNDING_STRESS}),
        period_end=PERIOD_END,
        available_at=AS_OF - timedelta(hours=1),
        as_of=AS_OF,
    )
    narrative = NarrativeSnapshot(
        snapshot_id=f"{prefix}-narrative",
        ticker="TEST",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        model_version="narrative-v1",
        thesis_id="test-thesis",
        thesis_version=1,
        kpi_set_version=1,
        kpi_definition_ids=("revenue",),
        assessments=(NarrativeAssessment(dimension="durability", state=NarrativeState.STRONG, evidence=("official customer data",)),),
        overall=NarrativeState.STRONG,
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
    )
    thesis = ThesisStatusSnapshot(
        snapshot_id=f"{prefix}-thesis-status",
        ticker="TEST",
        thesis_id="test-thesis",
        thesis_version=1,
        kpi_set_version=1,
        observation_ids=("obs-1",),
        status=thesis_status,
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
    )
    valuation = ValuationSnapshot(
        snapshot_id=f"{prefix}-valuation",
        ticker="TEST",
        assumption_set=assumptions(assumption_version),
        state=ResolutionState.RESOLVED,
        market_price=100,
        fundamental_input_fingerprint="fundamentals-v1",
        output=ValuationOutput(
            required_growth=0.12,
            expectation_gap=ExpectationGap.POSITIVE,
            bear_value=80,
            base_value=base_value,
            bull_value=160,
            downside_severity="moderate",
            upside_optionality="meaningful",
            asymmetry_type=AsymmetryType.FAVORABLE,
            confidence=ValuationConfidence.MEDIUM,
        ),
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
    )
    grade = InvestmentGradeSnapshot(
        snapshot_id=f"{prefix}-grade",
        ticker="TEST",
        model_version="investment-grade-v1",
        initial_valuation_grade=InvestmentGrade.A,
        final_grade=InvestmentGrade.B,
        adjustments=(
            InvestmentGradeAdjustment(sequence=1, adjustment_type=AdjustmentType.GATE, trigger=InvestmentGradeTrigger.NARRATIVE, active=True, reason="gate first"),
            InvestmentGradeAdjustment(sequence=2, adjustment_type=AdjustmentType.CAP, trigger=InvestmentGradeTrigger.FUNDING_STRESS, active=True, maximum_grade=InvestmentGrade.B, reason="cap second"),
        ),
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
    )
    return AnalysisSnapshot(
        snapshot_id=prefix,
        ticker="TEST",
        company_name="Test Company",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        case_definition_version="case1-v1-frozen",
        quant=quant,
        current_trend=current,
        narrative=narrative,
        thesis_status=thesis,
        valuation=valuation,
        investment_grade=grade,
        narrative_gate=NarrativeGate.CONFIRMED,
        reference_price_snapshot_id=f"{prefix}-price-reference",
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
    )


def register_assumption(session, version=1):
    ValuationRepository(session).add_valuation_assumption(
        assumptions(version), instrument_id="instrument-test", valid_from=AS_OF - timedelta(days=1), created_at=AS_OF
    )


def test_company_instrument_identity_and_exchange_aware_uniqueness(session):
    company, instrument = seed_identity(session)
    repo = IdentityRepository(session)
    repo.add_instrument(instrument.model_copy(update={"instrument_id": "instrument-nyse", "exchange": "NYSE"}))
    assert len(repo.list_company_instruments(company.company_id)) == 2
    with pytest.raises(IntegrityError):
        repo.add_instrument(instrument.model_copy(update={"instrument_id": "instrument-duplicate"}))


def test_source_provenance_round_trip(session):
    source = SourceReference(source_reference_id="sec-10k", source_type="sec", reference="https://www.sec.gov/example", filing_date=date(2026, 2, 1), period_end=date(2025, 12, 31), available_at=AS_OF - timedelta(days=200), retrieved_at=AS_OF, notes="official filing")
    repo = SourceRepository(session)
    repo.add_source_reference(source)
    assert repo.get_source_reference(source.source_reference_id) == source


def test_price_round_trip_negative_ev_duplicate_key_and_ordering(session):
    seed_identity(session)
    repo = PriceRepository(session)
    first = PriceSnapshot(price_snapshot_id="p1", ticker="TEST", company_id="company-test", timestamp=AS_OF - timedelta(days=1), price=10, currency="USD", market_cap=100, enterprise_value=-20, source="official close", price_type=PriceType.CLOSE, created_at=AS_OF)
    second = first.model_copy(update={"price_snapshot_id": "p2", "timestamp": AS_OF, "price": 11, "created_at": AS_OF + timedelta(minutes=1)})
    repo.add_price_snapshot(second, instrument_id="instrument-test")
    repo.add_price_snapshot(first, instrument_id="instrument-test")
    assert repo.get_price_snapshot("p1") == first
    assert repo.get_price_snapshot("p1").enterprise_value == -20
    assert [item.price_snapshot_id for item in repo.list_price_snapshots("instrument-test")] == ["p1", "p2"]
    with pytest.raises(IntegrityError):
        repo.add_price_snapshot(first.model_copy(update={"price_snapshot_id": "p3"}), instrument_id="instrument-test")


def test_naive_price_timestamp_rejected_before_persistence():
    with pytest.raises(ValidationError, match="timezone-aware"):
        PriceSnapshot(price_snapshot_id="naive", ticker="TEST", timestamp=AS_OF.replace(tzinfo=None), price=10, currency="USD", source="fixture", price_type=PriceType.EOD, created_at=AS_OF)


@pytest.mark.parametrize(
    "local_time",
    (
        datetime(2026, 9, 4, 9, tzinfo=ZoneInfo("Asia/Seoul")),
        datetime(2026, 1, 15, 9, tzinfo=ZoneInfo("America/New_York")),
        datetime(2026, 7, 15, 9, tzinfo=ZoneInfo("America/New_York")),
    ),
)
def test_price_timezone_round_trip_restores_same_utc_instant(session, local_time):
    seed_identity(session)
    snapshot = PriceSnapshot(
        price_snapshot_id=f"price-{local_time.month}",
        ticker="TEST",
        company_id="company-test",
        timestamp=local_time,
        price=10,
        currency="USD",
        source="official close",
        price_type=PriceType.CLOSE,
        created_at=local_time + timedelta(minutes=1),
    )
    repo = PriceRepository(session)
    repo.add_price_snapshot(snapshot, instrument_id="instrument-test")
    restored = repo.get_price_snapshot(snapshot.price_snapshot_id)
    assert restored.timestamp == local_time.astimezone(UTC)
    assert restored.timestamp.tzinfo == UTC
    assert restored.created_at == snapshot.created_at.astimezone(UTC)


def test_different_timezone_representations_restore_to_same_utc_instant(session):
    company = Company(
        company_id="same-instant",
        canonical_name="Same Instant",
        created_at=datetime(2026, 9, 4, 9, tzinfo=ZoneInfo("Asia/Seoul")),
    )
    repo = IdentityRepository(session)
    repo.add_company(company)
    restored = repo.get_company(company.company_id)
    assert restored.created_at == datetime(2026, 9, 3, 20, tzinfo=ZoneInfo("America/New_York"))
    assert restored.created_at.tzinfo == UTC


def test_source_analysis_and_kpi_times_restore_as_aware_utc(session):
    seed_identity(session)
    seoul = datetime(2026, 9, 4, 9, tzinfo=ZoneInfo("Asia/Seoul"))
    source = SourceReference(source_reference_id="timezone-source", source_type="sec", reference="official", available_at=seoul, retrieved_at=seoul + timedelta(minutes=1))
    source_repo = SourceRepository(session)
    source_repo.add_source_reference(source)
    restored_source = source_repo.get_source_reference(source.source_reference_id)
    assert restored_source.available_at == seoul.astimezone(UTC)
    assert restored_source.available_at.tzinfo == UTC

    register_assumption(session)
    analysis = full_analysis("timezone-analysis")
    AnalysisRepository(session).add_analysis_snapshot(analysis, instrument_id="instrument-test", company_id="company-test", created_at=seoul)
    restored_analysis = AnalysisRepository(session).get_analysis_snapshot(analysis.snapshot_id)
    assert restored_analysis.as_of.tzinfo == UTC
    assert restored_analysis.quant.available_at.tzinfo == UTC

    thesis_repo = ThesisRepository(session)
    thesis_repo.add_thesis_definition(thesis(1), instrument_id="instrument-test", created_at=AS_OF)
    thesis_repo.add_kpi_definition(kpi_definition(1), instrument_id="instrument-test")
    new_york = datetime(2026, 7, 1, 9, tzinfo=ZoneInfo("America/New_York"))
    observation = TrackingKPIObservation(observation_id="timezone-observation", ticker="TEST", kpi_definition_id="revenue", kpi_key="revenue", thesis_version=1, kpi_set_version=1, state=ResolutionState.RESOLVED, value=100, period_end=PERIOD_END, available_at=new_york, as_of=new_york + timedelta(hours=1))
    thesis_repo.add_kpi_observation(observation, instrument_id="instrument-test", created_at=new_york + timedelta(hours=1))
    restored_observation = thesis_repo.list_kpi_observations("revenue")[0]
    assert restored_observation.available_at == new_york.astimezone(UTC)
    assert restored_observation.available_at.tzinfo == UTC


def test_naive_analysis_source_and_kpi_times_are_rejected(session):
    seed_identity(session)
    with pytest.raises(ValidationError, match="timezone-aware"):
        SourceReference(source_reference_id="naive-source", source_type="sec", reference="official", available_at=AS_OF.replace(tzinfo=None))
    register_assumption(session)
    naive_analysis = full_analysis("naive-analysis").model_copy(update={"as_of": AS_OF.replace(tzinfo=None)})
    with pytest.raises(ValueError, match="as_of must be timezone-aware"):
        AnalysisRepository(session).add_analysis_snapshot(naive_analysis, instrument_id="instrument-test", company_id="company-test", created_at=AS_OF)
    thesis_repo = ThesisRepository(session)
    thesis_repo.add_thesis_definition(thesis(1), instrument_id="instrument-test", created_at=AS_OF)
    thesis_repo.add_kpi_definition(kpi_definition(1), instrument_id="instrument-test")
    observation = TrackingKPIObservation(observation_id="naive-observation", ticker="TEST", kpi_definition_id="revenue", kpi_key="revenue", thesis_version=1, kpi_set_version=1, state=ResolutionState.RESOLVED, value=100, period_end=PERIOD_END, available_at=AS_OF, as_of=AS_OF).model_copy(update={"available_at": AS_OF.replace(tzinfo=None)})
    with pytest.raises(ValueError, match="available_at must be timezone-aware"):
        thesis_repo.add_kpi_observation(observation, instrument_id="instrument-test", created_at=AS_OF)


def test_full_analysis_round_trip_children_unresolved_and_order(session):
    seed_identity(session)
    register_assumption(session)
    snapshot = full_analysis()
    repo = AnalysisRepository(session)
    repo.add_analysis_snapshot(snapshot, instrument_id="instrument-test", company_id="company-test", created_at=AS_OF)
    restored = repo.get_analysis_snapshot(snapshot.snapshot_id)
    assert restored == snapshot
    assert restored.quant.metrics[1].state == ResolutionState.UNRESOLVED
    assert restored.quant.metrics[1].value is None
    assert [item.sequence for item in restored.investment_grade.adjustments] == [1, 2]
    metric_row = session.scalar(select(MetricResultRow).where(MetricResultRow.metric_key == "capital_efficiency"))
    assert metric_row.raw_value is None and metric_row.normalized_value is None


def test_persisted_analysis_is_immutable_and_correction_appends(session):
    seed_identity(session)
    register_assumption(session)
    repo = AnalysisRepository(session)
    original = full_analysis("original")
    repo.add_analysis_snapshot(original, instrument_id="instrument-test", company_id="company-test", created_at=AS_OF)
    row = session.get(AnalysisSnapshotRow, "original")
    row.ticker = "CHANGED"
    with pytest.raises(ImmutableRecordError):
        session.commit()
    session.rollback()
    correction = full_analysis("correction", base_value=125)
    repo.add_analysis_snapshot(correction, instrument_id="instrument-test", company_id="company-test", created_at=AS_OF + timedelta(minutes=1), supersedes_snapshot_id="original", revision_reason="corrected source mapping")
    assert repo.get_analysis_snapshot("original") == original
    assert repo.get_analysis_snapshot("correction") == correction
    correction_row = session.get(AnalysisSnapshotRow, "correction")
    assert correction_row.supersedes_snapshot_id == "original"
    assert correction_row.revision_reason == "corrected source mapping"


def test_child_failure_rolls_back_analysis_root(session):
    seed_identity(session)
    register_assumption(session)
    repo = AnalysisRepository(session)
    original = full_analysis("original")
    repo.add_analysis_snapshot(original, instrument_id="instrument-test", company_id="company-test", created_at=AS_OF)
    conflicting = full_analysis("new-root").model_copy(update={"quant": full_analysis("original").quant})
    with pytest.raises(IntegrityError):
        repo.add_analysis_snapshot(conflicting, instrument_id="instrument-test", company_id="company-test", created_at=AS_OF + timedelta(minutes=1))
    assert session.get(AnalysisSnapshotRow, "new-root") is None


def thesis(version):
    return ThesisDefinition(thesis_id="test-thesis", ticker="TEST", version=version, case=AnalysisCase.CASE_1_PROFITABLE_GROWTH, title=f"Thesis v{version}", thesis="Durable growth", failure_mode="Growth breaks", kpi_set_version=version, kpi_definition_ids=("revenue",), effective_from=AS_OF + timedelta(days=version - 2))


def kpi_definition(version):
    return TrackingKPIDefinition(kpi_definition_id="revenue", ticker="TEST", kpi_key="revenue", thesis_id="test-thesis", thesis_version=version, kpi_set_version=version, name="Revenue", unit="USD", direction=KPIDirection.HIGHER_IS_BETTER, source_requirement="official filing", confirming_condition="growth", weakening_condition="decline")


def test_thesis_and_kpi_versions_observation_and_lookahead(session):
    seed_identity(session)
    repo = ThesisRepository(session)
    for version in (1, 2):
        repo.add_thesis_definition(thesis(version), instrument_id="instrument-test", created_at=AS_OF + timedelta(days=version))
        repo.add_kpi_definition(kpi_definition(version), instrument_id="instrument-test", frequency="quarterly")
    assert repo.get_active_thesis_definition("test-thesis", AS_OF + timedelta(days=2)).version == 2
    assert repo.list_kpi_definitions("test-thesis", 1)[0].kpi_set_version == 1
    observation = TrackingKPIObservation(observation_id="obs-1", ticker="TEST", kpi_definition_id="revenue", kpi_key="revenue", thesis_version=2, kpi_set_version=2, state=ResolutionState.RESOLVED, value=120, source_reference="official filing", period_end=PERIOD_END, available_at=AS_OF, as_of=AS_OF)
    repo.add_kpi_observation(observation, instrument_id="instrument-test", created_at=AS_OF)
    assert repo.list_kpi_observations("revenue") == (observation,)
    mismatch = observation.model_copy(update={"observation_id": "obs-bad", "kpi_set_version": 1})
    with pytest.raises(ValueError, match="version/key mismatch"):
        repo.add_kpi_observation(mismatch, instrument_id="instrument-test", created_at=AS_OF)
    with pytest.raises(ValidationError, match="available_at cannot be later"):
        TrackingKPIObservation(observation_id="future", ticker="TEST", kpi_definition_id="revenue", kpi_key="revenue", thesis_version=2, kpi_set_version=2, state=ResolutionState.RESOLVED, value=130, period_end=PERIOD_END, available_at=AS_OF + timedelta(days=1), as_of=AS_OF)


def test_legacy_stable_is_neutral_in_domain_and_database(session):
    seed_identity(session)
    register_assumption(session)
    legacy = full_analysis().thesis_status.model_dump(mode="json") | {"status": "stable"}
    normalized = ThesisStatusSnapshot.model_validate(legacy)
    snapshot = full_analysis("legacy", thesis_status=normalized.status)
    AnalysisRepository(session).add_analysis_snapshot(snapshot, instrument_id="instrument-test", company_id="company-test", created_at=AS_OF)
    row = session.get(ThesisStatusSnapshotRow, "legacy-thesis-status")
    assert normalized.status == ThesisStatus.NEUTRAL
    assert row.status == "neutral"
    assert "stable" not in str(row.payload).lower()


def test_valuation_versions_and_price_only_snapshot_preserve_history(session):
    seed_identity(session)
    valuation_repo = ValuationRepository(session)
    for version in (1, 2):
        valuation_repo.add_valuation_assumption(assumptions(version), instrument_id="instrument-test", valid_from=AS_OF + timedelta(days=version), created_at=AS_OF + timedelta(days=version))
    assert [item.version for item in valuation_repo.list_valuation_assumptions("test-assumptions")] == [1, 2]
    evidence = session.scalars(select(ExitMultipleEvidenceRow).order_by(ExitMultipleEvidenceRow.band)).all()
    assert len(evidence) == 6
    assert {item.evidence_type for item in evidence} == {"company_history"}
    assert all(item.source_reference.startswith("official history") for item in evidence)
    analysis_repo = AnalysisRepository(session)
    first = full_analysis("price-old", assumption_version=1, base_value=120)
    second = full_analysis("price-new", assumption_version=1, base_value=110)
    analysis_repo.add_analysis_snapshot(first, instrument_id="instrument-test", company_id="company-test", created_at=AS_OF)
    analysis_repo.add_analysis_snapshot(second, instrument_id="instrument-test", company_id="company-test", created_at=AS_OF + timedelta(days=1))
    assert analysis_repo.get_analysis_snapshot("price-old").valuation.output.base_value == 120
    assert analysis_repo.get_analysis_snapshot("price-new").valuation.assumption_set.version == 1
