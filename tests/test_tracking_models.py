from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from engine.models import CapitalModel, Grade
from engine.tracking_models import (
    AdjustmentType,
    AnalysisCase,
    AnalysisSnapshot,
    AsymmetryType,
    CurrentTrendSignal,
    CurrentTrendSnapshot,
    DirectionState,
    ExecutablePriceSnapshot,
    ExitMultipleEvidenceSource,
    ExitMultipleRange,
    GradeCap,
    GrowthScope,
    InvestmentGrade,
    InvestmentGradeAdjustment,
    InvestmentGradeSnapshot,
    InvestmentGradeTrigger,
    MetricResult,
    NarrativeAssessment,
    NarrativeSnapshot,
    NarrativeState,
    QuantSnapshot,
    ResolutionState,
    SnapshotDiff,
    TerminalStage,
    TrendFlag,
    ValuationAssumptionSet,
    ValuationConfidence,
    ValuationOutput,
    ValuationSnapshot,
)


UTC = timezone.utc
ANNUAL_END = date(2025, 12, 31)
ANNUAL_AVAILABLE = datetime(2026, 2, 20, tzinfo=UTC)
AS_OF = datetime(2026, 9, 1, tzinfo=UTC)


def _metric(name: str, weight: float, grade: Grade = Grade.A) -> MetricResult:
    return MetricResult(
        name=name,
        state=ResolutionState.RESOLVED,
        value=0.25,
        unit="ratio",
        grade=grade,
        weight=weight,
    )


def _case1_quant() -> QuantSnapshot:
    weights = {
        "revenue_growth": 0.15,
        "operating_profit_growth": 0.15,
        "margin_trend": 0.10,
        "cash_economics": 0.10,
        "capital_efficiency": 0.20,
        "balance_sheet": 0.10,
        "dilution": 0.05,
        "per_share_growth": 0.15,
    }
    return QuantSnapshot(
        snapshot_id="quant-case1-2025",
        ticker="STRL",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        model_version="case1-quant-v1-frozen",
        period_end=ANNUAL_END,
        available_at=ANNUAL_AVAILABLE,
        as_of=AS_OF,
        metrics=tuple(_metric(name, weight) for name, weight in weights.items()),
        state=ResolutionState.RESOLVED,
        score=3.65,
        grade=Grade.A,
    )


def _case2_quant() -> QuantSnapshot:
    core = (
        _metric("revenue_growth", 0.30, Grade.A),
        _metric("gross_profit_growth", 0.15, Grade.A),
        _metric("cash_burn_trend", 0.15, Grade.X),
        _metric("runway", 0.15, Grade.C),
        _metric("dilution", 0.15, Grade.X),
        _metric("revenue_per_share_growth", 0.10, Grade.B),
    )
    supporting = (
        MetricResult(
            name="gross_margin_trend",
            state=ResolutionState.RESOLVED,
            value=0.02,
            unit="pct_point",
            weight=0,
            is_core=False,
        ),
        MetricResult(
            name="incremental_operating_margin",
            state=ResolutionState.UNRESOLVED,
            weight=0,
            is_core=False,
            note="not comparable",
        ),
        MetricResult(
            name="potential_dilution",
            state=ResolutionState.RESOLVED,
            value="watch",
            weight=0,
            is_core=False,
        ),
        MetricResult(
            name="growth_scope",
            state=ResolutionState.RESOLVED,
            value=GrowthScope.SAME_SCOPE.value,
            weight=0,
            is_core=False,
        ),
    )
    return QuantSnapshot(
        snapshot_id="quant-case2-2025",
        ticker="EARLY",
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-quant-v1-frozen",
        period_end=ANNUAL_END,
        available_at=ANNUAL_AVAILABLE,
        as_of=AS_OF,
        metrics=core + supporting,
        state=ResolutionState.RESOLVED,
        score=1.90,
        grade=Grade.D,
        grade_caps=(
            GradeCap(
                trigger="cash_burn_x_and_dilution_x",
                maximum_grade=Grade.D,
                active=True,
                reason="Case 2 Quant v1 guardrail",
            ),
        ),
        growth_scope=GrowthScope.SAME_SCOPE,
    )


def test_lookahead_validation_rejects_information_after_as_of():
    with pytest.raises(ValidationError, match="available_at cannot be later"):
        QuantSnapshot(
            snapshot_id="lookahead",
            ticker="TEST",
            case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
            model_version="v1",
            period_end=ANNUAL_END,
            available_at=datetime(2026, 9, 2, tzinfo=UTC),
            as_of=AS_OF,
            metrics=(_metric("only_metric", 1.0),),
            state=ResolutionState.RESOLVED,
            score=4.0,
            grade=Grade.A,
        )


def test_analysis_snapshot_is_immutable():
    snapshot = AnalysisSnapshot(
        snapshot_id="analysis-case1-2025",
        ticker="STRL",
        company_name="Sterling Infrastructure",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        case_definition_version="case1-v1-frozen",
        capital_model=CapitalModel.PROJECT_BASED,
        period_end=ANNUAL_END,
        available_at=ANNUAL_AVAILABLE,
        as_of=AS_OF,
        quant=_case1_quant(),
    )

    with pytest.raises(ValidationError, match="frozen"):
        snapshot.company_name = "Changed"  # type: ignore[misc]


def test_unresolved_metric_is_not_silently_zero():
    unresolved = MetricResult(
        name="runway",
        state=ResolutionState.UNRESOLVED,
        weight=1.0,
    )
    assert unresolved.value is None

    with pytest.raises(ValidationError, match="unresolved metric"):
        MetricResult(
            name="runway",
            state=ResolutionState.UNRESOLVED,
            value=0.0,
            weight=1.0,
        )


def test_supporting_metric_cannot_silently_change_core_weights():
    with pytest.raises(ValidationError, match="supporting metric weight"):
        MetricResult(
            name="gross_margin_trend",
            state=ResolutionState.RESOLVED,
            value=0.02,
            weight=0.05,
            is_core=False,
        )


def test_narrative_kpi_ids_cannot_change_without_version_increment():
    with pytest.raises(ValidationError, match="kpi_set_version"):
        SnapshotDiff(
            previous_snapshot_id="analysis-v1",
            current_snapshot_id="analysis-v2",
            previous_kpi_set_version=1,
            current_kpi_set_version=1,
            previous_kpi_definition_ids=("revenue", "customers"),
            current_kpi_definition_ids=("revenue", "backlog"),
            narrative_kpi_set_changed=True,
        )

    diff = SnapshotDiff(
        previous_snapshot_id="analysis-v1",
        current_snapshot_id="analysis-v2",
        previous_kpi_set_version=1,
        current_kpi_set_version=2,
        previous_kpi_definition_ids=("revenue", "customers"),
        current_kpi_definition_ids=("revenue", "backlog"),
        narrative_kpi_set_changed=True,
    )
    assert diff.current_kpi_set_version == 2


def test_price_only_revaluation_preserves_assumption_version():
    assumptions = ValuationAssumptionSet(
        assumption_set_id="strl-valuation-assumptions",
        version=3,
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        terminal_stage=TerminalStage.MATURE,
        exit_multiple_range=ExitMultipleRange(
            conservative=12,
            base=16,
            premium=20,
        ),
        exit_multiple_evidence=frozenset(
            {
                ExitMultipleEvidenceSource.COMPANY_HISTORY,
                ExitMultipleEvidenceSource.COMPARABLE_COMPANIES,
            }
        ),
    )
    original = ValuationSnapshot(
        snapshot_id="valuation-price-1",
        ticker="STRL",
        period_end=date(2026, 9, 1),
        available_at=datetime(2026, 9, 1, 20, tzinfo=UTC),
        as_of=datetime(2026, 9, 1, 21, tzinfo=UTC),
        assumption_set=assumptions,
        state=ResolutionState.RESOLVED,
        market_price=300,
        output=ValuationOutput(
            bear_value=220,
            base_value=340,
            bull_value=450,
            asymmetry_type=AsymmetryType.FAVORABLE,
            confidence=ValuationConfidence.MEDIUM,
        ),
    )
    repriced = original.reprice(
        snapshot_id="valuation-price-2",
        period_end=date(2026, 9, 2),
        available_at=datetime(2026, 9, 2, 20, tzinfo=UTC),
        as_of=datetime(2026, 9, 2, 21, tzinfo=UTC),
        market_price=320,
        output=ValuationOutput(
            bear_value=220,
            base_value=340,
            bull_value=450,
            asymmetry_type=AsymmetryType.BALANCED,
            confidence=ValuationConfidence.MEDIUM,
        ),
    )

    assert original.market_price == 300
    assert repriced.market_price == 320
    assert repriced.assumption_set == original.assumption_set
    assert repriced.assumption_set.version == 3


def test_case1_analysis_snapshot_example():
    current = CurrentTrendSnapshot(
        snapshot_id="current-case1-h1-2026",
        ticker="STRL",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        model_version="case1-current-v1-frozen",
        period_end=date(2026, 6, 30),
        available_at=datetime(2026, 8, 4, tzinfo=UTC),
        as_of=AS_OF,
        signals=(
            CurrentTrendSignal(name="revenue_growth", state=DirectionState.POSITIVE),
            CurrentTrendSignal(name="cash_economics", state=DirectionState.NEUTRAL),
        ),
        overall=DirectionState.POSITIVE,
    )
    snapshot = AnalysisSnapshot(
        snapshot_id="analysis-case1-example",
        ticker="STRL",
        company_name="Sterling Infrastructure",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        case_definition_version="case1-v1-frozen",
        capital_model=CapitalModel.PROJECT_BASED,
        period_end=date(2026, 6, 30),
        available_at=datetime(2026, 8, 4, tzinfo=UTC),
        as_of=AS_OF,
        quant=_case1_quant(),
        current_trend=current,
    )

    assert snapshot.quant.grade == Grade.A
    assert len(snapshot.quant.metrics) == 8
    assert snapshot.current_trend.overall == DirectionState.POSITIVE


def test_case2_analysis_snapshot_example_and_guardrail():
    narrative = NarrativeSnapshot(
        snapshot_id="narrative-case2-2025",
        ticker="EARLY",
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-narrative-v1",
        thesis_id="early-commercial-thesis",
        thesis_version=1,
        kpi_set_version=1,
        kpi_definition_ids=("revenue", "customers"),
        assessments=tuple(
            NarrativeAssessment(dimension=dimension, state=NarrativeState.EMERGING)
            for dimension in (
                "differentiation",
                "defensibility",
                "adoption",
                "penetration_expansion",
                "durability",
                "failure_mode",
            )
        ),
        overall=NarrativeState.EMERGING,
        period_end=ANNUAL_END,
        available_at=ANNUAL_AVAILABLE,
        as_of=AS_OF,
    )
    snapshot = AnalysisSnapshot(
        snapshot_id="analysis-case2-example",
        ticker="EARLY",
        company_name="Early Commercial Company",
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        case_definition_version="case2-v1-frozen",
        period_end=ANNUAL_END,
        available_at=ANNUAL_AVAILABLE,
        as_of=AS_OF,
        quant=_case2_quant(),
        narrative=narrative,
    )

    assert snapshot.quant.growth_scope == GrowthScope.SAME_SCOPE
    assert snapshot.quant.grade_caps[0].maximum_grade == Grade.D
    assert snapshot.quant.grade_caps[0].active is True
    assert snapshot.narrative.overall == NarrativeState.EMERGING


def test_investment_grade_cap_trigger_is_representable():
    snapshot = InvestmentGradeSnapshot(
        snapshot_id="investment-grade-1",
        ticker="EARLY",
        model_version="investment-grade-v1",
        period_end=date(2026, 6, 30),
        available_at=datetime(2026, 8, 10, tzinfo=UTC),
        as_of=AS_OF,
        initial_valuation_grade=InvestmentGrade.B,
        final_grade=InvestmentGrade.D,
        adjustments=(
            InvestmentGradeAdjustment(
                adjustment_type=AdjustmentType.CAP,
                trigger=InvestmentGradeTrigger.FUNDING_STRESS,
                active=True,
                maximum_grade=InvestmentGrade.D,
                reason="funding stress caps the initial valuation grade",
            ),
        ),
    )

    assert snapshot.adjustments[0].trigger == InvestmentGradeTrigger.FUNDING_STRESS
    assert snapshot.adjustments[0].maximum_grade == InvestmentGrade.D


def test_commercial_inflection_flag_is_representable():
    snapshot = CurrentTrendSnapshot(
        snapshot_id="current-case2-inflection",
        ticker="EARLY",
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-current-v1",
        period_end=date(2026, 6, 30),
        available_at=datetime(2026, 8, 10, tzinfo=UTC),
        as_of=AS_OF,
        signals=(
            CurrentTrendSignal(
                name="revenue_momentum",
                state=DirectionState.STRONG_POSITIVE,
            ),
        ),
        overall=DirectionState.STRONG_POSITIVE,
        flags=frozenset({TrendFlag.COMMERCIAL_INFLECTION}),
    )

    assert TrendFlag.COMMERCIAL_INFLECTION in snapshot.flags


def test_funding_stress_flag_is_representable():
    snapshot = CurrentTrendSnapshot(
        snapshot_id="current-case2-funding",
        ticker="EARLY",
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-current-v1",
        period_end=date(2026, 6, 30),
        available_at=datetime(2026, 8, 10, tzinfo=UTC),
        as_of=AS_OF,
        signals=(
            CurrentTrendSignal(
                name="funding_runway",
                state=DirectionState.NEGATIVE,
            ),
        ),
        overall=DirectionState.NEGATIVE,
        flags=frozenset({TrendFlag.FUNDING_STRESS}),
    )

    assert TrendFlag.FUNDING_STRESS in snapshot.flags


def test_historical_price_cannot_precede_information_release():
    with pytest.raises(ValidationError, match="cannot precede"):
        ExecutablePriceSnapshot(
            information_available_at=datetime(2026, 2, 20, 13, tzinfo=UTC),
            executable_at=datetime(2025, 12, 31, 21, tzinfo=UTC),
            price=100,
            source_reference="official exchange close",
        )
