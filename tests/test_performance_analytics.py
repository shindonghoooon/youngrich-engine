from datetime import date, datetime, timezone

import pytest

from engine.models import Grade
from engine.performance_analytics import CohortDimension, analyze_performance_cohorts
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
    HorizonPerformance,
    InvestmentGrade,
    InvestmentGradeAdjustment,
    InvestmentGradeSnapshot,
    InvestmentGradeTrigger,
    MetricResult,
    PerformanceHorizon,
    PerformanceReturnType,
    PerformanceSnapshot,
    PriceBasis,
    PriceSeriesCoverage,
    PriceSeriesCoverageStatus,
    QuantSnapshot,
    ResolutionState,
    TerminalStage,
    ThesisStatus,
    ThesisStatusSnapshot,
    TrendFlag,
    ValuationAssumptionSet,
    ValuationConfidence,
    ValuationMetric,
    ValuationOutput,
    ValuationSnapshot,
)


UTC = timezone.utc
NOW = datetime(2026, 9, 1, 20, tzinfo=UTC)
END = date(2025, 12, 31)


def assumptions():
    return ValuationAssumptionSet(
        assumption_set_id="cohort-assumptions",
        version=1,
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        horizon_years=3,
        terminal_stage=TerminalStage.MATURE,
        terminal_stage_rationale="cohort fixture",
        terminal_stage_confidence=ValuationConfidence.HIGH,
        primary_metric=ValuationMetric.PE,
        exit_multiples=tuple(ExitMultipleAssumption(band=band, metric_type=ValuationMetric.PE, value=value, evidence_type=ExitMultipleEvidenceSource.COMPANY_HISTORY, source_reference="fixture", as_of=NOW, rationale="fixture") for band, value in zip(ExitMultipleBand, (10, 15, 20), strict=True)),
        plausible_growth_range=AssumptionRange(low=0.10, high=0.20),
    )


def historical_analysis(identifier, investment_grade, *, quant_grade=Grade.A):
    quant = QuantSnapshot(snapshot_id=f"{identifier}-quant", ticker=identifier, case=AnalysisCase.CASE_1_PROFITABLE_GROWTH, model_version="case1-v1-frozen", metrics=(MetricResult(name="quality", state=ResolutionState.RESOLVED, value=1, grade=quant_grade, weight=1.0),), state=ResolutionState.RESOLVED, score=4.0, grade=quant_grade, period_end=END, available_at=NOW, as_of=NOW)
    current = CurrentTrendSnapshot(snapshot_id=f"{identifier}-current", ticker=identifier, case=AnalysisCase.CASE_1_PROFITABLE_GROWTH, model_version="current-v1-frozen", signals=(CurrentTrendSignal(name="revenue", state=DirectionState.POSITIVE),), overall=DirectionState.POSITIVE, flags=frozenset({TrendFlag.FUNDING_STRESS, TrendFlag.COMMERCIAL_INFLECTION}), period_end=END, available_at=NOW, as_of=NOW)
    thesis = ThesisStatusSnapshot(snapshot_id=f"{identifier}-thesis", ticker=identifier, thesis_id=f"{identifier}-thesis-definition", thesis_version=1, kpi_set_version=1, observation_ids=(), status=ThesisStatus.CONFIRMING, period_end=END, available_at=NOW, as_of=NOW)
    valuation = ValuationSnapshot(snapshot_id=f"{identifier}-valuation", ticker=identifier, assumption_set=assumptions(), state=ResolutionState.RESOLVED, market_price=100, output=ValuationOutput(required_growth=0.10, expectation_gap=ExpectationGap.POSITIVE, asymmetry_type=AsymmetryType.FAVORABLE, confidence=ValuationConfidence.HIGH), period_end=END, available_at=NOW, as_of=NOW)
    grade = InvestmentGradeSnapshot(snapshot_id=f"{identifier}-grade", ticker=identifier, model_version="investment-grade-v1", initial_valuation_grade=investment_grade, final_grade=investment_grade, adjustments=(InvestmentGradeAdjustment(sequence=1, adjustment_type=AdjustmentType.GATE, trigger=InvestmentGradeTrigger.QUANT, active=False, reason="historical fixture"),), period_end=END, available_at=NOW, as_of=NOW)
    return AnalysisSnapshot(snapshot_id=identifier, ticker=identifier, company_name=identifier, case=AnalysisCase.CASE_1_PROFITABLE_GROWTH, case_definition_version="case1-v1-frozen", quant=quant, current_trend=current, thesis_status=thesis, valuation=valuation, investment_grade=grade, reference_price_snapshot_id=f"{identifier}-start", period_end=END, available_at=NOW, as_of=NOW)


def performance(identifier, analysis_id, value, *, alpha=None, drawdown=-0.10):
    horizons = []
    for item in PerformanceHorizon:
        if item == PerformanceHorizon.ONE_YEAR and value is not None:
            benchmark = {} if alpha is None else {
                "benchmark_end_price_snapshot_id": f"{identifier}-benchmark-end",
                "benchmark_end_price": 105,
                "benchmark_return": value - alpha,
                "benchmark_return_type": PerformanceReturnType.PRICE_RETURN,
                "benchmark_start_effective_date": date(2026, 9, 1),
                "benchmark_end_effective_date": date(2027, 9, 1),
                "alpha_state": ResolutionState.RESOLVED,
                "alpha": alpha,
            }
            horizons.append(HorizonPerformance(horizon=item, state=ResolutionState.RESOLVED, target_date=date(2027, 9, 1), end_price_snapshot_id=f"{identifier}-end", end_price=100 * (1 + value), stock_return=value, stock_start_effective_date=date(2026, 9, 1), stock_end_effective_date=date(2027, 9, 1), **benchmark))
        else:
            horizons.append(HorizonPerformance(horizon=item, state=ResolutionState.UNRESOLVED, target_date=date(2027, 9, 1)))
    benchmark_root = {} if alpha is None else {
        "benchmark_assignment_id": "benchmark",
        "benchmark_assignment_version": 1,
        "benchmark_instrument_id": "benchmark-instrument",
        "benchmark_return_type": PerformanceReturnType.PRICE_RETURN,
        "benchmark_price_basis": PriceBasis.SPLIT_ADJUSTED,
        "benchmark_start_price_snapshot_id": f"{identifier}-benchmark-start",
        "benchmark_start_price": 100,
    }
    mdd_coverage = (PriceSeriesCoverage(status=PriceSeriesCoverageStatus.SUFFICIENT, observation_count=2, first_timestamp=datetime(2026, 9, 1, 20, tzinfo=UTC), last_timestamp=datetime(2027, 9, 1, 20, tzinfo=UTC), maximum_observed_gap_days=7) if drawdown is not None else PriceSeriesCoverage(status=PriceSeriesCoverageStatus.INSUFFICIENT, observation_count=0, reason="fixture has no complete MDD series"))
    return PerformanceSnapshot(performance_snapshot_id=f"{identifier}-performance", ticker=analysis_id, analysis_snapshot_id=analysis_id, instrument_id=f"{analysis_id}-instrument", evaluation_as_of=datetime(2027, 9, 1, 20, tzinfo=UTC), return_type=PerformanceReturnType.PRICE_RETURN, price_basis=PriceBasis.SPLIT_ADJUSTED, start_price_snapshot_id=f"{analysis_id}-start", start_price=100, horizons=tuple(horizons), return_since_analysis=value, max_drawdown=drawdown, mdd_coverage=mdd_coverage, state=ResolutionState.RESOLVED, coverage=0.25 if value is not None else 0.0, calculation_version="performance-v1", created_at=datetime(2027, 9, 1, 21, tzinfo=UTC), **benchmark_root)


def test_grade_cohorts_expose_samples_and_exclude_unresolved_per_metric():
    specs = (
        ("a1", InvestmentGrade.A, 0.10, 0.05),
        ("a2", InvestmentGrade.A, 0.20, None),
        ("a3", InvestmentGrade.A, -0.10, -0.02),
        ("b1", InvestmentGrade.B, 0.05, None),
        ("b2", InvestmentGrade.B, 0.15, None),
        ("c1", InvestmentGrade.C, None, None),
    )
    records = []
    for identifier, grade, value, alpha in specs:
        snapshot = historical_analysis(identifier, grade)
        records.append((performance(identifier, identifier, value, alpha=alpha, drawdown=None if identifier == "c1" else -0.10), snapshot))
    results = {item.cohort: item for item in analyze_performance_cohorts(records, dimension=CohortDimension.INVESTMENT_GRADE, horizon=PerformanceHorizon.ONE_YEAR)}
    assert results["A"].snapshot_count == 3
    assert results["A"].return_sample_count == 3
    assert results["A"].mean_return == pytest.approx(0.20 / 3)
    assert results["A"].median_return == pytest.approx(0.10)
    assert results["A"].positive_return_rate == pytest.approx(2 / 3)
    assert results["A"].alpha_sample_count == 2
    assert results["B"].return_sample_count == 2
    assert results["C"].snapshot_count == 1
    assert results["C"].return_sample_count == 0
    assert results["C"].mean_return is None
    assert results["C"].positive_return_rate is None


@pytest.mark.parametrize(
    ("dimension", "expected"),
    (
        (CohortDimension.CASE, "case1_profitable_growth"),
        (CohortDimension.INVESTMENT_GRADE, "A"),
        (CohortDimension.QUANT_GRADE, "A"),
        (CohortDimension.EXPECTATION_GAP, "positive"),
        (CohortDimension.ASYMMETRY_TYPE, "favorable"),
        (CohortDimension.VALUATION_CONFIDENCE, "high"),
        (CohortDimension.THESIS_STATUS, "confirming"),
        (CohortDimension.FUNDING_STRESS, "true"),
        (CohortDimension.COMMERCIAL_INFLECTION, "true"),
    ),
)
def test_supported_historical_cohort_dimensions(dimension, expected):
    snapshot = historical_analysis("sample", InvestmentGrade.A)
    result = analyze_performance_cohorts(((performance("sample", "sample", 0.10), snapshot),), dimension=dimension, horizon=PerformanceHorizon.ONE_YEAR)
    assert result[0].cohort == expected


def test_performance_must_pair_with_its_historical_snapshot():
    snapshot = historical_analysis("analysis", InvestmentGrade.A)
    with pytest.raises(ValueError, match="paired"):
        analyze_performance_cohorts(((performance("p", "different", 0.10), snapshot),), dimension=CohortDimension.CASE, horizon=PerformanceHorizon.ONE_YEAR)


def test_multiple_evaluations_of_one_analysis_are_not_double_counted():
    snapshot = historical_analysis("repeat", InvestmentGrade.A)
    early = performance("early", "repeat", None)
    later = performance("later", "repeat", 0.10).model_copy(update={
        "evaluation_as_of": early.evaluation_as_of.replace(year=2028),
        "created_at": early.created_at.replace(year=2028),
    })
    result = analyze_performance_cohorts(((early, snapshot), (later, snapshot)), dimension=CohortDimension.INVESTMENT_GRADE, horizon=PerformanceHorizon.ONE_YEAR)[0]
    assert result.evaluation_snapshot_count == 2
    assert result.snapshot_count == 1
    assert result.return_sample_count == 1


def test_newer_unresolved_evaluation_does_not_replace_resolved_horizon():
    snapshot = historical_analysis("resolved-wins", InvestmentGrade.B)
    resolved = performance("resolved", "resolved-wins", 0.25)
    unresolved = performance("unresolved", "resolved-wins", None).model_copy(
        update={
            "evaluation_as_of": datetime(2027, 10, 1, 20, tzinfo=UTC),
            "created_at": datetime(2027, 10, 1, 21, tzinfo=UTC),
        }
    )
    result = analyze_performance_cohorts(
        ((resolved, snapshot), (unresolved, snapshot)),
        dimension=CohortDimension.INVESTMENT_GRADE,
        horizon=PerformanceHorizon.ONE_YEAR,
    )[0]
    assert result.evaluation_snapshot_count == 2
    assert result.snapshot_count == 1
    assert result.return_sample_count == 1
    assert result.mean_return == pytest.approx(0.25)


def test_missing_current_state_is_unresolved_not_false():
    snapshot = historical_analysis("unknown-current", InvestmentGrade.C).model_copy(
        update={"current_trend": None}
    )
    result = analyze_performance_cohorts(
        ((performance("unknown-current", "unknown-current", 0.10), snapshot),),
        dimension=CohortDimension.FUNDING_STRESS,
        horizon=PerformanceHorizon.ONE_YEAR,
    )[0]
    assert result.cohort == "unresolved"


def test_auditable_research_cohort_label_does_not_mutate_snapshot():
    snapshot = historical_analysis("labeled", InvestmentGrade.C)
    before = snapshot.model_dump()
    result = analyze_performance_cohorts(
        ((performance("labeled", "labeled", 0.10), snapshot),),
        dimension=CohortDimension.EXPECTATION_GAP,
        horizon=PerformanceHorizon.ONE_YEAR,
        cohort_labels={snapshot.snapshot_id: "negative"},
    )[0]
    assert result.cohort == "negative"
    assert snapshot.model_dump() == before
