from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.calibration_analytics import (
    analyze_incremental_layers,
    analyze_metric_grades,
    calculate_layer_coverage,
    compare_logic_versions,
    extract_research_candidates,
    metric_observations,
)
from engine.calibration_engine import build_calibration_record
from engine.calibration_models import (
    CalibrationLayer,
    CalibrationDataQuality,
    CalibrationRunMode,
    CaseEvaluationHorizon,
    LogicVersionSet,
    ResearchConfidence,
    ResearchFinding,
    ResearchFindingStatus,
    ResearchFindingType,
    ResearchScreen,
    ResearchSignalLayer,
    build_calibration_run,
)
from engine.case_backtest_adapters import (
    Case1BacktestAdapter,
    Case1BacktestInput,
    CaseBacktestAdapter,
    evaluate_with_adapter,
)
from engine.financials import load_financial_history
from engine.models import CapitalModel, Grade
from engine.tracking_models import (
    AnalysisCase,
    AnalysisSnapshot,
    AssumptionRange,
    CurrentTrendSignal,
    CurrentTrendSnapshot,
    DirectionState,
    ExitMultipleAssumption,
    ExitMultipleBand,
    ExitMultipleEvidenceSource,
    InvestmentGrade,
    InvestmentGradeSnapshot,
    HorizonPerformance,
    MetricResult,
    NarrativeAssessment,
    NarrativeSnapshot,
    NarrativeState,
    PerformanceHorizon,
    PerformanceReturnType,
    PerformanceSnapshot,
    PriceBasis,
    PriceSeriesCoverage,
    PriceSeriesCoverageStatus,
    QuantSnapshot,
    ResolutionState,
    TerminalStage,
    ValuationAssumptionSet,
    ValuationConfidence,
    ValuationMetric,
    ValuationOutput,
    ValuationSnapshot,
)


UTC = timezone.utc
AS_OF = datetime(2021, 3, 1, 21, tzinfo=UTC)
END = date(2020, 12, 31)
AVAILABLE = datetime(2021, 2, 20, 21, tzinfo=UTC)
RAW_DATA = Path(__file__).parents[1] / "data" / "raw"


def run_for(
    *,
    run_id: str = "run-v1",
    quant_version: str = "quant-v1",
    case: str = AnalysisCase.CASE_1_PROFITABLE_GROWTH.value,
    case_version: str = "case-v1",
    current_version: str | None = None,
    valuation_version: str | None = None,
    investment_grade_version: str | None = None,
):
    return build_calibration_run(
        run_id=run_id,
        calibration_version="calibration-v1",
        git_commit="abc123",
        created_at=datetime(2026, 9, 4, tzinfo=UTC),
        universe_version="fixture-v1",
        data_version="offline-v1",
        start_date=date(2020, 1, 1),
        end_date=date(2025, 12, 31),
        included_cases=(case,),
        logic_versions=(LogicVersionSet(
            case=case,
            case_version=case_version,
            quant_engine_version=quant_version,
            current_engine_version=current_version,
            valuation_version=valuation_version,
            investment_grade_version=investment_grade_version,
        ),),
        performance_version="performance-v1",
        benchmark_policy_version=None,
        run_mode=CalibrationRunMode.PILOT,
        primary_evaluation_horizons=(CaseEvaluationHorizon(
            case=case,
            primary_evaluation_horizon=PerformanceHorizon.ONE_YEAR,
        ),),
    )


def analysis(
    *,
    identifier: str = "analysis-v1",
    metric_key: str = "revenue_growth",
    metric_value: float = 0.20,
    metric_grade: Grade = Grade.A,
    quant_version: str = "quant-v1",
    current: bool = False,
    valuation: bool = False,
    narrative: bool = False,
    investment_grade: bool = False,
    case: AnalysisCase = AnalysisCase.CASE_1_PROFITABLE_GROWTH,
) -> AnalysisSnapshot:
    quant = QuantSnapshot(
        snapshot_id=f"{identifier}-quant",
        ticker="TEST",
        case=case,
        model_version=quant_version,
        period_end=END,
        available_at=AVAILABLE,
        as_of=AS_OF,
        metrics=(MetricResult(
            name=metric_key,
            state=ResolutionState.RESOLVED,
            value=metric_value,
            unit="ratio",
            grade=metric_grade,
            weight=1.0,
        ),),
        state=ResolutionState.RESOLVED,
        score=4.0,
        grade=metric_grade,
    )
    current_snapshot = CurrentTrendSnapshot(
        snapshot_id=f"{identifier}-current",
        ticker="TEST",
        case=case,
        model_version="current-v1",
        period_end=END,
        available_at=AVAILABLE,
        as_of=AS_OF,
        signals=(CurrentTrendSignal(name="direction", state=DirectionState.POSITIVE),),
        overall=DirectionState.POSITIVE,
    ) if current else None
    narrative_snapshot = NarrativeSnapshot(
        snapshot_id=f"{identifier}-narrative",
        ticker="TEST",
        case=case,
        model_version="narrative-v1",
        thesis_id="thesis",
        thesis_version=1,
        kpi_set_version=1,
        kpi_definition_ids=("kpi",),
        assessments=(NarrativeAssessment(
            dimension="durability", state=NarrativeState.STRONG
        ),),
        overall=NarrativeState.STRONG,
        period_end=END,
        available_at=AVAILABLE,
        as_of=AS_OF,
    ) if narrative else None
    valuation_snapshot = None
    if valuation:
        assumptions = ValuationAssumptionSet(
            assumption_set_id="valuation",
            version=1,
            case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
            horizon_years=3,
            terminal_stage=TerminalStage.MATURE,
            terminal_stage_rationale="test",
            terminal_stage_confidence=ValuationConfidence.MEDIUM,
            primary_metric=ValuationMetric.PE,
            plausible_growth_range=AssumptionRange(low=0.1, high=0.2),
            exit_multiples=tuple(
                ExitMultipleAssumption(
                    band=band,
                    metric_type=ValuationMetric.PE,
                    value=value,
                    evidence_type=ExitMultipleEvidenceSource.COMPANY_HISTORY,
                    source_reference="point-in-time test",
                    as_of=AS_OF,
                    rationale="test",
                )
                for band, value in zip(ExitMultipleBand, (10, 15, 20), strict=True)
            ),
        )
        valuation_snapshot = ValuationSnapshot(
            snapshot_id=f"{identifier}-valuation",
            ticker="TEST",
            assumption_set=assumptions,
            state=ResolutionState.RESOLVED,
            market_price=100,
            output=ValuationOutput(
                required_growth=0.15,
                bear_value=80,
                base_value=120,
                bull_value=160,
                confidence=ValuationConfidence.MEDIUM,
            ),
            period_end=END,
            available_at=AVAILABLE,
            as_of=AS_OF,
        )
    grade_snapshot = InvestmentGradeSnapshot(
        snapshot_id=f"{identifier}-ig",
        ticker="TEST",
        model_version="ig-v1",
        initial_valuation_grade=InvestmentGrade.A,
        final_grade=InvestmentGrade.A,
        period_end=END,
        available_at=AVAILABLE,
        as_of=AS_OF,
    ) if investment_grade else None
    return AnalysisSnapshot(
        snapshot_id=identifier,
        ticker="TEST",
        company_name="Test Company",
        case=case,
        case_definition_version="case-v1",
        quant=quant,
        current_trend=current_snapshot,
        narrative=narrative_snapshot,
        valuation=valuation_snapshot,
        investment_grade=grade_snapshot,
        period_end=END,
        available_at=AVAILABLE,
        as_of=AS_OF,
    )


def performance(
    analysis_id: str,
    *,
    identifier: str = "performance-v1",
    resolved: bool = True,
    one_year_return: float = 0.20,
) -> PerformanceSnapshot:
    horizons = tuple(
        HorizonPerformance(
            horizon=horizon,
            state=ResolutionState.RESOLVED if resolved else ResolutionState.UNRESOLVED,
            target_date=date(2022, 3, 1),
            end_price_snapshot_id=f"end-{horizon.value}" if resolved else None,
            end_price=100 * (1 + one_year_return) if resolved else None,
            stock_return=one_year_return if resolved else None,
            stock_start_effective_date=AS_OF.date() if resolved else None,
            stock_end_effective_date=date(2022, 3, 1) if resolved else None,
        )
        for horizon in PerformanceHorizon
    )
    coverage = PriceSeriesCoverage(
        status=(PriceSeriesCoverageStatus.SUFFICIENT if resolved else PriceSeriesCoverageStatus.UNRESOLVED),
        observation_count=2 if resolved else 0,
        first_timestamp=AS_OF if resolved else None,
        last_timestamp=AS_OF + timedelta(days=365) if resolved else None,
        maximum_observed_gap_days=1 if resolved else None,
        reason=None if resolved else "future outcome unavailable",
    )
    return PerformanceSnapshot(
        performance_snapshot_id=identifier,
        ticker="TEST",
        analysis_snapshot_id=analysis_id,
        instrument_id="instrument",
        evaluation_as_of=AS_OF + timedelta(days=365),
        return_type=PerformanceReturnType.PRICE_RETURN,
        price_basis=PriceBasis.SPLIT_ADJUSTED,
        start_price_snapshot_id="start" if resolved else None,
        start_price=100 if resolved else None,
        horizons=horizons,
        return_since_analysis=one_year_return if resolved else None,
        max_drawdown=-0.10 if resolved else None,
        mdd_coverage=coverage,
        state=ResolutionState.RESOLVED if resolved else ResolutionState.UNRESOLVED,
        coverage=1.0 if resolved else 0.0,
        calculation_version="performance-v1",
        created_at=AS_OF + timedelta(days=365, minutes=1),
    )


def joined(item: AnalysisSnapshot, *, record_id: str = "record", resolved=True, one_year_return=0.20):
    perf = performance(item.snapshot_id, identifier=f"{record_id}-performance", resolved=resolved, one_year_return=one_year_return)
    record = build_calibration_record(
        record_id=record_id,
        run=run_for(
            quant_version=item.quant.model_version,
            case=item.case.value,
            current_version=(item.current_trend.model_version if item.current_trend else None),
            valuation_version=(
                f"{item.valuation.assumption_set.assumption_set_id}:v{item.valuation.assumption_set.version}"
                if item.valuation else None
            ),
            investment_grade_version=(
                item.investment_grade.model_version if item.investment_grade else None
            ),
        ),
        analysis=item,
        performance=perf,
        company_id="company",
        instrument_id="instrument",
        data_quality=CalibrationDataQuality.COMPLETE if resolved else CalibrationDataQuality.UNRESOLVED,
        source_scope="offline-test",
    )
    return record, item, perf


def test_calibration_run_hash_is_reproducible_and_version_sensitive():
    first = run_for(run_id="first")
    second = run_for(run_id="second")
    changed = run_for(run_id="changed", quant_version="quant-v2")
    assert first.config_hash == second.config_hash
    assert changed.config_hash != first.config_hash


def test_record_links_snapshots_retains_unresolved_and_does_not_mutate_analysis():
    item = analysis()
    before = item.model_dump()
    record, _item, perf = joined(item, resolved=False)
    assert record.performance_snapshot_id == perf.performance_snapshot_id
    assert record.performance_state == ResolutionState.UNRESOLVED
    assert record.data_quality == CalibrationDataQuality.UNRESOLVED
    assert item.model_dump() == before


def test_case1_adapter_calls_frozen_engine_and_builds_canonical_snapshot():
    history = load_financial_history(RAW_DATA / "STRL.json")
    inputs = Case1BacktestInput(
        snapshot_id="strl-calibration",
        quant_snapshot_id="strl-calibration-quant",
        history=history,
        capital_model=CapitalModel.PROJECT_BASED,
        available_at=datetime(2026, 2, 20, tzinfo=UTC),
        as_of=datetime(2026, 3, 1, tzinfo=UTC),
    )
    result = evaluate_with_adapter(Case1BacktestAdapter(), inputs, as_of=inputs.as_of)
    assert isinstance(result, AnalysisSnapshot)
    assert result.quant.score == pytest.approx(3.65)
    assert len(result.quant.metrics) == 8
    evaluation = datetime(2027, 3, 1, tzinfo=UTC)
    perf = performance(result.snapshot_id, resolved=False).model_copy(
        update={
            "ticker": "STRL",
            "evaluation_as_of": evaluation,
            "created_at": evaluation + timedelta(minutes=1),
        }
    )
    record = build_calibration_record(
        record_id="strl-record",
        run=build_calibration_run(
            run_id="strl-run",
            calibration_version="calibration-v1",
            git_commit="abc123",
            created_at=datetime(2026, 9, 4, tzinfo=UTC),
            universe_version="fixture-v1",
            data_version="STRL-raw-v1",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 12, 31),
            included_cases=(Case1BacktestAdapter.case,),
            logic_versions=(LogicVersionSet(
                case=Case1BacktestAdapter.case,
                case_version=Case1BacktestAdapter.logic_version,
                quant_engine_version=Case1BacktestAdapter.quant_engine_version,
            ),),
            performance_version="performance-v1",
            run_mode=CalibrationRunMode.PILOT,
            primary_evaluation_horizons=(CaseEvaluationHorizon(
                case=Case1BacktestAdapter.case,
                primary_evaluation_horizon=PerformanceHorizon.ONE_YEAR,
            ),),
        ),
        analysis=result,
        performance=perf,
        company_id="strl-company",
        instrument_id="instrument",
        data_quality=CalibrationDataQuality.UNRESOLVED,
        source_scope="official-fixture",
    )
    assert record.analysis_snapshot_id == result.snapshot_id


def test_dummy_case3_adapter_plugs_into_kernel_without_case_branching():
    class DummyAdapter:
        case = "case3_dummy_cyclical"
        logic_version = "case3-test-only-v1"

        def is_eligible(self, inputs, as_of):
            return True

        def evaluate(self, inputs, as_of):
            return SimpleNamespace(
                snapshot_id="dummy-analysis",
                ticker="DUMMY",
                case=self.case,
                case_definition_version=self.logic_version,
                as_of=as_of,
                quant=SimpleNamespace(model_version="dummy-quant-v1"),
                current_trend=None,
                valuation=None,
                investment_grade=None,
            )

    adapter: CaseBacktestAdapter[object] = DummyAdapter()
    result = evaluate_with_adapter(adapter, object(), as_of=AS_OF)
    perf = performance("dummy-analysis", resolved=False).model_copy(update={"ticker": "DUMMY"})
    record = build_calibration_record(
        record_id="dummy-record",
        run=run_for(
            case=adapter.case,
            case_version=adapter.logic_version,
            quant_version="dummy-quant-v1",
        ),
        analysis=result,
        performance=perf,
        company_id="dummy-company",
        instrument_id="instrument",
        data_quality=CalibrationDataQuality.UNRESOLVED,
        source_scope="test-only",
    )
    assert record.case == "case3_dummy_cyclical"


@pytest.mark.parametrize("metric_key", ("revenue_growth", "runway", "inventory_signal"))
def test_generic_metric_analytics_accepts_case1_case2_and_unknown_keys(metric_key):
    case = (
        AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH.value
        if metric_key == "runway" else AnalysisCase.CASE_1_PROFITABLE_GROWTH.value
    )
    item = analysis(
        metric_key=metric_key,
        case=(
            AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
            if metric_key == "runway" else AnalysisCase.CASE_1_PROFITABLE_GROWTH
        ),
    )
    observation = joined(item)
    result = analyze_metric_grades(
        (observation,),
        case=case,
        metric_key=metric_key,
        horizon=PerformanceHorizon.ONE_YEAR,
    )
    assert result[0].metric_key == metric_key
    assert result[0].median_return == pytest.approx(0.20)
    extracted = metric_observations(
        observation, normalized_values={metric_key: 1.0}
    )[0]
    assert extracted.raw_value == 0.20
    assert extracted.normalized_value == 1.0


def test_layer_coverage_counts_progressive_resolution():
    items = (
        analysis(identifier="quant"),
        analysis(identifier="current", current=True),
        analysis(identifier="valuation", current=True, valuation=True),
        analysis(identifier="full", current=True, valuation=True, narrative=True, investment_grade=True),
    )
    observations = tuple(joined(item, record_id=f"record-{index}") for index, item in enumerate(items))
    result = calculate_layer_coverage(observations)
    assert result.model_dump() == {
        "total_records": 4,
        "quant_resolved": 4,
        "current_resolved": 3,
        "valuation_resolved": 2,
        "narrative_resolved": 1,
        "full_investment_grade_resolved": 1,
    }
    layer_stats = analyze_incremental_layers(
        observations, horizon=PerformanceHorizon.ONE_YEAR
    )
    by_layer = {item.layer: item for item in layer_stats}
    assert by_layer[CalibrationLayer.QUANT].layer_resolved_count == 4
    assert by_layer[CalibrationLayer.QUANT_CURRENT].layer_resolved_count == 3
    assert by_layer[CalibrationLayer.QUANT_CURRENT_VALUATION].layer_resolved_count == 2
    assert by_layer[CalibrationLayer.FULL_INVESTMENT_GRADE].layer_resolved_count == 1
    assert all(item.eligible_record_count == 4 for item in layer_stats)


def test_same_outcome_logic_versions_can_coexist_and_be_compared():
    previous = analysis(identifier="v1", metric_value=0.20, quant_version="quant-v1")
    current = analysis(identifier="v2", metric_value=0.30, metric_grade=Grade.B, quant_version="quant-v2")
    previous_join = joined(previous, record_id="previous")
    current_join = joined(current, record_id="current")
    comparison = compare_logic_versions(previous_join, current_join)
    assert comparison.previous_quant_version == "quant-v1"
    assert comparison.current_quant_version == "quant-v2"
    assert comparison.metric_changes[0].previous_value == 0.20
    assert comparison.metric_changes[0].current_value == 0.30


def test_false_positive_and_negative_screens_are_research_configurable():
    strong = joined(analysis(identifier="strong", metric_grade=Grade.A), record_id="strong", one_year_return=-0.40)
    weak = joined(analysis(identifier="weak", metric_grade=Grade.X), record_id="weak", one_year_return=1.20)
    false_positive = extract_research_candidates(
        (strong, weak),
        screen=ResearchScreen(
            layer=ResearchSignalLayer.QUANT,
            grades=frozenset({"A", "B"}),
            horizon=PerformanceHorizon.ONE_YEAR,
            maximum_return=-0.30,
        ),
    )
    false_negative = extract_research_candidates(
        (strong, weak),
        screen=ResearchScreen(
            layer=ResearchSignalLayer.QUANT,
            grades=frozenset({"D", "X"}),
            horizon=PerformanceHorizon.ONE_YEAR,
            minimum_return=1.00,
        ),
    )
    assert [item.calibration_record_id for item in false_positive] == ["strong"]
    assert [item.calibration_record_id for item in false_negative] == ["weak"]


def test_research_finding_cannot_mutate_frozen_policy():
    finding = ResearchFinding(
        finding_id="finding",
        calibration_run_id="run-v1",
        component="runway",
        finding_type=ResearchFindingType.METRIC_NON_MONOTONIC,
        description="descriptive pattern",
        evidence_summary="ordered cohort table",
        sample_count=20,
        confidence_level=ResearchConfidence.LOW,
        status=ResearchFindingStatus.REQUIRES_VALIDATION,
    )
    with pytest.raises(RuntimeError, match="ADR/design review"):
        finding.policy_change()
