from datetime import date, datetime, timedelta, timezone

import pytest

from engine.models import Grade
from engine.snapshot_diff import build_snapshot_diff
from engine.tracking_models import (
    AnalysisCase,
    AnalysisSnapshot,
    AssumptionRange,
    AsymmetryType,
    ChangeState,
    CurrentTrendSignal,
    CurrentTrendSnapshot,
    DirectionState,
    ExitMultipleAssumption,
    ExitMultipleBand,
    ExitMultipleEvidenceSource,
    GradeChangeReason,
    InvestmentGrade,
    InvestmentGradeSnapshot,
    MetricResult,
    NarrativeAssessment,
    NarrativeGate,
    NarrativeSnapshot,
    NarrativeState,
    QuantSnapshot,
    ResolutionState,
    TerminalStage,
    ThesisStatus,
    ThesisStatusSnapshot,
    TrendFlag,
    ValuationAssumptionSet,
    ValuationChangeType,
    ValuationConfidence,
    ValuationMetric,
    ValuationOutput,
    ValuationSnapshot,
    ExpectationGap,
)


UTC = timezone.utc
BASE = datetime(2026, 8, 1, tzinfo=UTC)


def assumptions(version, case):
    metric = ValuationMetric.PE if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH else ValuationMetric.EV_REVENUE
    return ValuationAssumptionSet(
        assumption_set_id="stable-assumptions", version=version, case=case,
        horizon_years=3 if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH else 5,
        terminal_stage=TerminalStage.MATURE if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH else TerminalStage.GROWTH,
        terminal_stage_rationale="synthetic", terminal_stage_confidence=ValuationConfidence.MEDIUM,
        primary_metric=metric,
        exit_multiples=tuple(ExitMultipleAssumption(band=band, metric_type=metric, value=value, evidence_type=ExitMultipleEvidenceSource.COMPARABLE_COMPANIES, source_reference="fixture", as_of=BASE, rationale="fixture") for band, value in zip(ExitMultipleBand, (4, 5, 6), strict=True)),
        plausible_growth_range=AssumptionRange(low=0.20, high=0.40),
        expected_annual_dilution=0.05 if case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH else None,
        terminal_net_debt=0 if case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH else None,
    )


def snapshot(
    revision,
    *,
    case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
    metric_grade=Grade.C,
    metric_state=ResolutionState.RESOLVED,
    metric_value=0.10,
    overall=DirectionState.NEUTRAL,
    signal=DirectionState.NEUTRAL,
    flags=frozenset(),
    narrative_state=NarrativeState.EMERGING,
    narrative_gate=NarrativeGate.QUALIFIED,
    thesis_status=ThesisStatus.NEUTRAL,
    thesis_breaker=False,
    gap=ExpectationGap.NEGATIVE,
    asymmetry=AsymmetryType.UNFAVORABLE,
    confidence=ValuationConfidence.MEDIUM,
    investment_grade=InvestmentGrade.C,
    price=100,
    assumption_version=1,
    fundamental_fingerprint=None,
):
    as_of = BASE + timedelta(days=revision)
    period_end = date(2026, 6, 30)
    metric = MetricResult(name="dilution", state=metric_state, value=metric_value if metric_state == ResolutionState.RESOLVED else None, grade=metric_grade if metric_state == ResolutionState.RESOLVED else None, weight=1.0)
    quant = QuantSnapshot(snapshot_id=f"q-{revision}", ticker="TEST", case=case, model_version="frozen", period_end=period_end, available_at=BASE, as_of=as_of, metrics=(metric,), state=metric_state, score=2.0 if metric_state == ResolutionState.RESOLVED else None, grade=metric_grade if metric_state == ResolutionState.RESOLVED else None)
    current = CurrentTrendSnapshot(snapshot_id=f"c-{revision}", ticker="TEST", case=case, model_version="frozen", period_end=period_end, available_at=BASE, as_of=as_of, signals=(CurrentTrendSignal(name="revenue_momentum", state=signal),), overall=overall, flags=flags)
    narrative = NarrativeSnapshot(snapshot_id=f"n-{revision}", ticker="TEST", case=case, model_version="frozen", thesis_id="thesis", thesis_version=1, kpi_set_version=1, kpi_definition_ids=("revenue", "adoption"), assessments=tuple(NarrativeAssessment(dimension=dimension, state=narrative_state) for dimension in ("differentiation", "defensibility", "adoption", "penetration_expansion", "durability", "failure_mode")), overall=narrative_state, period_end=period_end, available_at=BASE, as_of=as_of)
    thesis = ThesisStatusSnapshot(snapshot_id=f"t-{revision}", ticker="TEST", thesis_id="thesis", thesis_version=1, kpi_set_version=1, observation_ids=("one", "two"), status=thesis_status, breaker_triggered=thesis_breaker, period_end=period_end, available_at=BASE, as_of=as_of)
    valuation = ValuationSnapshot(snapshot_id=f"v-{revision}", ticker="TEST", assumption_set=assumptions(assumption_version, case), state=ResolutionState.RESOLVED, market_price=price if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH else None, market_cap=price * 100 if case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH else None, fundamental_input_fingerprint=fundamental_fingerprint, output=ValuationOutput(required_growth=0.30, expectation_gap=gap, asymmetry_type=asymmetry, confidence=confidence), period_end=period_end, available_at=as_of, as_of=as_of)
    grade = InvestmentGradeSnapshot(snapshot_id=f"ig-{revision}", ticker="TEST", model_version="frozen", initial_valuation_grade=investment_grade, final_grade=investment_grade, thesis_breaker_active=thesis_breaker, period_end=period_end, available_at=as_of, as_of=as_of)
    return AnalysisSnapshot(snapshot_id=f"a-{revision}", ticker="TEST", company_name="Test", case=case, case_definition_version="frozen", quant=quant, current_trend=current, narrative=narrative, narrative_gate=narrative_gate, thesis_status=thesis, valuation=valuation, investment_grade=grade, reference_price_snapshot_id=f"p-{revision}", period_end=period_end, available_at=as_of, as_of=as_of)


def reasons(diff):
    return diff.grade_attribution.reasons


def test_requires_same_company_and_strict_chronology():
    previous = snapshot(1)
    with pytest.raises(ValueError, match="same ticker"):
        build_snapshot_diff(previous, snapshot(2).model_copy(update={"ticker": "OTHER"}))
    with pytest.raises(ValueError, match="later"):
        build_snapshot_diff(previous, previous)


def test_quant_metric_grade_semantics_and_unresolved_transitions():
    deterioration = build_snapshot_diff(snapshot(1, metric_grade=Grade.C, metric_value=0.05), snapshot(2, metric_grade=Grade.D, metric_value=0.12))
    assert deterioration.metric_changes[0].change == ChangeState.DETERIORATED
    resolved = build_snapshot_diff(snapshot(1, metric_state=ResolutionState.UNRESOLVED, metric_grade=None, metric_value=None), snapshot(2))
    assert resolved.metric_changes[0].change == ChangeState.RESOLVED
    lost = build_snapshot_diff(snapshot(1), snapshot(2, metric_state=ResolutionState.UNRESOLVED, metric_grade=None, metric_value=None))
    assert lost.metric_changes[0].change == ChangeState.BECAME_UNRESOLVED


def test_current_narrative_and_flag_transitions_are_structured_and_material():
    previous = snapshot(1, signal=DirectionState.NEGATIVE, narrative_state=NarrativeState.EMERGING)
    current = snapshot(2, signal=DirectionState.POSITIVE, narrative_state=NarrativeState.STRONG, flags=frozenset({TrendFlag.COMMERCIAL_INFLECTION}))
    diff = build_snapshot_diff(previous, current)
    assert diff.signal_changes[0].change == ChangeState.IMPROVED
    assert all(item.change == ChangeState.IMPROVED for item in diff.narrative_changes)
    assert diff.flag_changes[0].material is True
    assert "commercial_inflection" in diff.material_changes


def test_price_only_upgrade_and_expensive_company_downgrade_attribution():
    upgrade = build_snapshot_diff(snapshot(1, gap=ExpectationGap.NEGATIVE, investment_grade=InvestmentGrade.C, price=100), snapshot(2, gap=ExpectationGap.OVERLAP, investment_grade=InvestmentGrade.B, price=50))
    assert upgrade.valuation_change_type == ValuationChangeType.PRICE_ONLY
    assert GradeChangeReason.PRICE in reasons(upgrade)
    assert GradeChangeReason.QUANT not in reasons(upgrade)
    assert GradeChangeReason.NARRATIVE not in reasons(upgrade)
    downgrade = build_snapshot_diff(snapshot(1, case=AnalysisCase.CASE_1_PROFITABLE_GROWTH, metric_grade=Grade.A, gap=ExpectationGap.POSITIVE, investment_grade=InvestmentGrade.A, price=100), snapshot(2, case=AnalysisCase.CASE_1_PROFITABLE_GROWTH, metric_grade=Grade.A, gap=ExpectationGap.NEGATIVE, investment_grade=InvestmentGrade.D, price=300))
    assert downgrade.valuation_change_type == ValuationChangeType.PRICE_ONLY
    assert reasons(downgrade) == frozenset({GradeChangeReason.PRICE})


def test_assumption_only_and_mixed_valuation_classification():
    assumption_change = build_snapshot_diff(snapshot(1), snapshot(2, assumption_version=2))
    assert assumption_change.valuation_change_type == ValuationChangeType.ASSUMPTION_CHANGE
    mixed = build_snapshot_diff(snapshot(1), snapshot(2, assumption_version=2, price=80))
    assert mixed.valuation_change_type == ValuationChangeType.MIXED
    fundamental_and_price = build_snapshot_diff(snapshot(1, fundamental_fingerprint="fundamentals-v1"), snapshot(2, price=80, fundamental_fingerprint="fundamentals-v2"))
    assert fundamental_and_price.valuation_change_type == ValuationChangeType.MIXED


def test_onds_price_decline_cannot_escape_funding_cap():
    previous = snapshot(1, flags=frozenset({TrendFlag.FUNDING_STRESS}), gap=ExpectationGap.NEGATIVE, investment_grade=InvestmentGrade.C, price=100)
    current = snapshot(2, flags=frozenset({TrendFlag.FUNDING_STRESS}), gap=ExpectationGap.OVERLAP, investment_grade=InvestmentGrade.C, price=40)
    diff = build_snapshot_diff(previous, current)
    assert diff.valuation_change_type == ValuationChangeType.PRICE_ONLY
    assert diff.grade_attribution.previous_grade == diff.grade_attribution.current_grade == InvestmentGrade.C
    assert not diff.grade_attribution.reasons


def test_funding_quant_and_breaker_attribution():
    funding = build_snapshot_diff(snapshot(1, investment_grade=InvestmentGrade.B), snapshot(2, flags=frozenset({TrendFlag.FUNDING_STRESS}), investment_grade=InvestmentGrade.C))
    assert GradeChangeReason.FUNDING in reasons(funding)
    quant = build_snapshot_diff(snapshot(1, metric_grade=Grade.B, investment_grade=InvestmentGrade.B), snapshot(2, metric_grade=Grade.D, investment_grade=InvestmentGrade.C))
    assert GradeChangeReason.QUANT in reasons(quant)
    broken = build_snapshot_diff(snapshot(1, investment_grade=InvestmentGrade.B), snapshot(2, thesis_status=ThesisStatus.BROKEN, thesis_breaker=True, investment_grade=InvestmentGrade.X))
    assert GradeChangeReason.THESIS_BREAKER in reasons(broken)
    assert "thesis_broken" in broken.material_changes


def test_multiple_causes_and_case_migration_are_preserved():
    previous = snapshot(1, metric_grade=Grade.C, investment_grade=InvestmentGrade.C)
    current = snapshot(2, case=AnalysisCase.CASE_1_PROFITABLE_GROWTH, metric_grade=Grade.A, signal=DirectionState.POSITIVE, narrative_state=NarrativeState.STRONG, narrative_gate=NarrativeGate.CONFIRMED, gap=ExpectationGap.OVERLAP, investment_grade=InvestmentGrade.B, price=80, assumption_version=2)
    diff = build_snapshot_diff(previous, current)
    assert "case_migration" in diff.material_changes
    assert {GradeChangeReason.CASE_MIGRATION, GradeChangeReason.QUANT, GradeChangeReason.CURRENT_TREND, GradeChangeReason.NARRATIVE, GradeChangeReason.MULTIPLE}.issubset(reasons(diff))


def test_tem_thesis_strengthening_is_detected_without_quant_change():
    previous = snapshot(1, metric_grade=Grade.B, narrative_state=NarrativeState.STRONG, thesis_status=ThesisStatus.NEUTRAL, investment_grade=InvestmentGrade.B)
    current = snapshot(2, metric_grade=Grade.B, narrative_state=NarrativeState.PROVEN, thesis_status=ThesisStatus.CONFIRMING, investment_grade=InvestmentGrade.B)
    diff = build_snapshot_diff(previous, current)
    assert all(item.change == ChangeState.IMPROVED for item in diff.narrative_changes)
    assert not any(item.metric_key == "dilution" and item.change != ChangeState.UNCHANGED for item in diff.metric_changes)
    assert next(item for item in diff.changes if item.field == "thesis_status").current == "confirming"
