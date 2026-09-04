"""Generic descriptive analytics over joined calibration records."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Iterable, Mapping

from engine.calibration_models import (
    CalibrationRecord,
    CalibrationLayer,
    LayerCoverage,
    LayerOutcomeStatistics,
    LogicVersionComparison,
    MetricCohortStatistics,
    MetricResearchObservation,
    MetricVersionChange,
    ResearchCandidate,
    ResearchScreen,
    ResearchSignalLayer,
)
from engine.tracking_models import (
    AnalysisSnapshot,
    DirectionState,
    InvestmentGrade,
    NarrativeState,
    PerformanceHorizon,
    PerformanceSnapshot,
    ResolutionState,
)
from engine.performance_analytics import (
    CohortDimension,
    CohortStatistics,
    analyze_performance_cohorts,
)


CalibrationObservation = tuple[CalibrationRecord, AnalysisSnapshot, PerformanceSnapshot]


def _validate_join(observation: CalibrationObservation) -> None:
    record, analysis, performance = observation
    if record.analysis_snapshot_id != analysis.snapshot_id:
        raise ValueError("CalibrationRecord must reference its AnalysisSnapshot")
    if record.performance_snapshot_id != performance.performance_snapshot_id:
        raise ValueError("CalibrationRecord must reference its PerformanceSnapshot")


def _horizon(
    performance: PerformanceSnapshot,
    horizon: PerformanceHorizon,
):
    return next(item for item in performance.horizons if item.horizon == horizon)


def metric_observations(
    observation: CalibrationObservation,
    *,
    normalized_values: Mapping[str, float | str | bool | None] | None = None,
) -> tuple[MetricResearchObservation, ...]:
    """Expose existing raw MetricResult data; normalization is an optional research view."""
    _validate_join(observation)
    record, analysis, _performance = observation
    normalized_values = normalized_values or {}
    return tuple(
        MetricResearchObservation(
            calibration_record_id=record.record_id,
            analysis_snapshot_id=analysis.snapshot_id,
            case=record.case,
            metric_key=metric.name,
            state=metric.state,
            raw_value=metric.value,
            normalized_value=normalized_values.get(metric.name),
            metric_grade=metric.grade.value if metric.grade else None,
            unit=metric.unit,
        )
        for metric in analysis.quant.metrics
    )


def analyze_metric_grades(
    observations: Iterable[CalibrationObservation],
    *,
    case: str,
    metric_key: str,
    horizon: PerformanceHorizon,
) -> tuple[MetricCohortStatistics, ...]:
    """Describe outcomes by any metric key without knowing metric semantics."""
    grouped: dict[str, list[tuple[PerformanceSnapshot, float]]] = defaultdict(list)
    for observation in observations:
        _validate_join(observation)
        record, analysis, performance = observation
        if record.case != case:
            continue
        metric = next(
            (item for item in analysis.quant.metrics if item.name == metric_key), None
        )
        if metric is None:
            continue
        result = _horizon(performance, horizon)
        if result.state != ResolutionState.RESOLVED or result.stock_return is None:
            continue
        grade = metric.grade.value if metric.grade else "unresolved"
        grouped[grade].append((performance, result.stock_return))

    order = {grade: index for index, grade in enumerate(("A", "B", "C", "D", "X", "unresolved"))}
    output: list[MetricCohortStatistics] = []
    for grade, items in sorted(grouped.items(), key=lambda pair: order.get(pair[0], 99)):
        returns = [item[1] for item in items]
        drawdowns = [
            performance.max_drawdown
            for performance, _value in items
            if performance.max_drawdown is not None
        ]
        alphas = [
            result.alpha
            for performance, _value in items
            for result in (_horizon(performance, horizon),)
            if result.alpha is not None
        ]
        output.append(MetricCohortStatistics(
            case=case,
            metric_key=metric_key,
            metric_grade=grade,
            horizon=horizon,
            sample_count=len(returns),
            mean_return=mean(returns),
            median_return=median(returns),
            positive_return_rate=sum(value > 0 for value in returns) / len(returns),
            median_max_drawdown=median(drawdowns) if drawdowns else None,
            median_alpha=median(alphas) if alphas else None,
        ))
    return tuple(output)


def calculate_layer_coverage(
    observations: Iterable[CalibrationObservation],
) -> LayerCoverage:
    items = tuple(observations)
    for item in items:
        _validate_join(item)
    analyses = [item[1] for item in items]
    return LayerCoverage(
        total_records=len(analyses),
        quant_resolved=sum(
            item.quant.state == ResolutionState.RESOLVED for item in analyses
        ),
        current_resolved=sum(
            item.current_trend is not None
            and item.current_trend.overall != DirectionState.UNRESOLVED
            for item in analyses
        ),
        valuation_resolved=sum(
            item.valuation is not None
            and item.valuation.state == ResolutionState.RESOLVED
            for item in analyses
        ),
        narrative_resolved=sum(
            item.narrative is not None
            and item.narrative.overall != NarrativeState.UNRESOLVED
            for item in analyses
        ),
        full_investment_grade_resolved=sum(
            item.investment_grade is not None
            and item.investment_grade.final_grade != InvestmentGrade.U
            for item in analyses
        ),
    )


def analyze_incremental_layers(
    observations: Iterable[CalibrationObservation],
    *,
    horizon: PerformanceHorizon,
) -> tuple[LayerOutcomeStatistics, ...]:
    """Report each richer layer on the same eligible cohort with explicit coverage."""
    items = tuple(observations)
    for item in items:
        _validate_join(item)

    def layer_is_resolved(layer: CalibrationLayer, analysis: AnalysisSnapshot) -> bool:
        quant = analysis.quant.state == ResolutionState.RESOLVED
        current = (
            analysis.current_trend is not None
            and analysis.current_trend.overall != DirectionState.UNRESOLVED
        )
        valuation = (
            analysis.valuation is not None
            and analysis.valuation.state == ResolutionState.RESOLVED
        )
        narrative = (
            analysis.narrative is not None
            and analysis.narrative.overall != NarrativeState.UNRESOLVED
        )
        full_grade = (
            analysis.investment_grade is not None
            and analysis.investment_grade.final_grade != InvestmentGrade.U
        )
        return {
            CalibrationLayer.QUANT: quant,
            CalibrationLayer.QUANT_CURRENT: quant and current,
            CalibrationLayer.QUANT_CURRENT_VALUATION: quant and current and valuation,
            CalibrationLayer.FULL_INVESTMENT_GRADE: (
                quant and current and valuation and narrative and full_grade
            ),
        }[layer]

    output: list[LayerOutcomeStatistics] = []
    for layer in CalibrationLayer:
        resolved = [item for item in items if layer_is_resolved(layer, item[1])]
        returns = [
            result.stock_return
            for _record, _analysis, performance in resolved
            for result in (_horizon(performance, horizon),)
            if result.state == ResolutionState.RESOLVED and result.stock_return is not None
        ]
        output.append(LayerOutcomeStatistics(
            layer=layer,
            eligible_record_count=len(items),
            layer_resolved_count=len(resolved),
            return_sample_count=len(returns),
            mean_return=mean(returns) if returns else None,
            median_return=median(returns) if returns else None,
            positive_return_rate=(
                sum(value > 0 for value in returns) / len(returns) if returns else None
            ),
        ))
    return tuple(output)


def analyze_calibration_cohorts(
    observations: Iterable[CalibrationObservation],
    *,
    dimension: CohortDimension,
    horizon: PerformanceHorizon,
    cohort_labels: Mapping[str, str | None] | None = None,
) -> tuple[CohortStatistics, ...]:
    """Reuse the common cohort engine after validating calibration joins."""
    items = tuple(observations)
    for item in items:
        _validate_join(item)
    return analyze_performance_cohorts(
        ((performance, analysis) for _record, analysis, performance in items),
        dimension=dimension,
        horizon=horizon,
        cohort_labels=cohort_labels,
    )


def extract_research_candidates(
    observations: Iterable[CalibrationObservation],
    *,
    screen: ResearchScreen,
) -> tuple[ResearchCandidate, ...]:
    """Apply an explicitly supplied research screen; it is not investment policy."""
    candidates: list[ResearchCandidate] = []
    for observation in observations:
        _validate_join(observation)
        record, analysis, performance = observation
        if screen.layer == ResearchSignalLayer.QUANT:
            grade = analysis.quant.grade.value if analysis.quant.grade else None
        else:
            grade = (
                analysis.investment_grade.final_grade.value
                if analysis.investment_grade else None
            )
        if grade not in screen.grades:
            continue
        result = _horizon(performance, screen.horizon)
        if result.state != ResolutionState.RESOLVED or result.stock_return is None:
            continue
        if screen.maximum_return is not None and result.stock_return > screen.maximum_return:
            continue
        if screen.minimum_return is not None and result.stock_return < screen.minimum_return:
            continue
        candidates.append(ResearchCandidate(
            calibration_record_id=record.record_id,
            company_id=record.company_id,
            ticker=analysis.ticker,
            analysis_as_of=analysis.as_of,
            case=record.case,
            matched_grade=grade,
            horizon=screen.horizon,
            future_return=result.stock_return,
            metrics=metric_observations(observation),
            current_signal=(analysis.current_trend.overall if analysis.current_trend else None),
            expectation_gap=(analysis.valuation.output.expectation_gap.value if analysis.valuation else None),
        ))
    return tuple(candidates)


def compare_logic_versions(
    previous: CalibrationObservation,
    current: CalibrationObservation,
) -> LogicVersionComparison:
    """Compare logic versions on identical identity, time, and future outcomes."""
    _validate_join(previous)
    _validate_join(current)
    previous_record, previous_analysis, previous_performance = previous
    current_record, current_analysis, current_performance = current
    identity_before = (
        previous_record.company_id,
        previous_record.instrument_id,
        previous_analysis.as_of,
    )
    identity_after = (
        current_record.company_id,
        current_record.instrument_id,
        current_analysis.as_of,
    )
    if identity_before != identity_after:
        raise ValueError("logic comparison requires identical company, instrument, and as_of")
    outcome_before = tuple(
        (item.horizon, item.state, item.stock_return, item.alpha)
        for item in previous_performance.horizons
    )
    outcome_after = tuple(
        (item.horizon, item.state, item.stock_return, item.alpha)
        for item in current_performance.horizons
    )
    if outcome_before != outcome_after:
        raise ValueError("logic comparison requires identical future outcomes")

    before_metrics = {item.name: item for item in previous_analysis.quant.metrics}
    after_metrics = {item.name: item for item in current_analysis.quant.metrics}
    changes = tuple(
        MetricVersionChange(
            metric_key=key,
            previous_value=before_metrics.get(key).value if key in before_metrics else None,
            current_value=after_metrics.get(key).value if key in after_metrics else None,
            previous_grade=(before_metrics[key].grade.value if key in before_metrics and before_metrics[key].grade else None),
            current_grade=(after_metrics[key].grade.value if key in after_metrics and after_metrics[key].grade else None),
        )
        for key in sorted(set(before_metrics) | set(after_metrics))
        if (
            before_metrics.get(key).value if key in before_metrics else None,
            before_metrics[key].grade if key in before_metrics else None,
        ) != (
            after_metrics.get(key).value if key in after_metrics else None,
            after_metrics[key].grade if key in after_metrics else None,
        )
    )
    return LogicVersionComparison(
        company_id=previous_record.company_id,
        instrument_id=previous_record.instrument_id,
        analysis_as_of=previous_analysis.as_of,
        previous_record_id=previous_record.record_id,
        current_record_id=current_record.record_id,
        previous_quant_version=previous_analysis.quant.model_version,
        current_quant_version=current_analysis.quant.model_version,
        previous_quant_grade=(previous_analysis.quant.grade.value if previous_analysis.quant.grade else None),
        current_quant_grade=(current_analysis.quant.grade.value if current_analysis.quant.grade else None),
        metric_changes=changes,
        coverage_changed=previous_analysis.quant.coverage != current_analysis.quant.coverage,
    )
