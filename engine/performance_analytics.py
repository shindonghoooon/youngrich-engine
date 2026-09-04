"""Descriptive cohort analytics over immutable historical analysis context."""

from __future__ import annotations

from enum import Enum
from statistics import mean, median
from typing import Iterable, Mapping

from pydantic import Field

from engine.tracking_models import (
    AnalysisSnapshot,
    FrozenDomainModel,
    PerformanceHorizon,
    PerformanceSnapshot,
    ResolutionState,
    TrendFlag,
)


class CohortDimension(str, Enum):
    CASE = "case"
    INVESTMENT_GRADE = "investment_grade"
    QUANT_GRADE = "quant_grade"
    EXPECTATION_GAP = "expectation_gap"
    ASYMMETRY_TYPE = "asymmetry_type"
    VALUATION_CONFIDENCE = "valuation_confidence"
    THESIS_STATUS = "thesis_status"
    FUNDING_STRESS = "funding_stress"
    COMMERCIAL_INFLECTION = "commercial_inflection"


class CohortStatistics(FrozenDomainModel):
    dimension: CohortDimension
    cohort: str
    horizon: PerformanceHorizon
    evaluation_snapshot_count: int = Field(ge=0)
    snapshot_count: int = Field(ge=0)
    return_sample_count: int = Field(ge=0)
    mean_return: float | None = None
    median_return: float | None = None
    minimum_return: float | None = None
    maximum_return: float | None = None
    positive_return_rate: float | None = None
    alpha_sample_count: int = Field(ge=0)
    mean_alpha: float | None = None
    median_alpha: float | None = None
    drawdown_sample_count: int = Field(ge=0)
    mean_max_drawdown: float | None = None
    median_max_drawdown: float | None = None


def _cohort_key(analysis: AnalysisSnapshot, dimension: CohortDimension) -> str:
    if dimension == CohortDimension.CASE:
        return analysis.case.value
    if dimension == CohortDimension.INVESTMENT_GRADE:
        return analysis.investment_grade.final_grade.value if analysis.investment_grade else "unresolved"
    if dimension == CohortDimension.QUANT_GRADE:
        return analysis.quant.grade.value if analysis.quant.grade else "unresolved"
    if dimension == CohortDimension.EXPECTATION_GAP:
        return analysis.valuation.output.expectation_gap.value if analysis.valuation else "unresolved"
    if dimension == CohortDimension.ASYMMETRY_TYPE:
        return analysis.valuation.output.asymmetry_type.value if analysis.valuation else "unresolved"
    if dimension == CohortDimension.VALUATION_CONFIDENCE:
        return analysis.valuation.output.confidence.value if analysis.valuation else "unresolved"
    if dimension == CohortDimension.THESIS_STATUS:
        return analysis.thesis_status.status.value if analysis.thesis_status else "unresolved"
    if dimension == CohortDimension.FUNDING_STRESS:
        if analysis.current_trend is None:
            return "unresolved"
        return str(TrendFlag.FUNDING_STRESS in analysis.current_trend.flags).lower()
    if dimension == CohortDimension.COMMERCIAL_INFLECTION:
        if analysis.current_trend is None:
            return "unresolved"
        return str(TrendFlag.COMMERCIAL_INFLECTION in analysis.current_trend.flags).lower()
    raise ValueError(f"unsupported cohort dimension: {dimension}")


def _stats(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return mean(values), median(values)


def analyze_performance_cohorts(
    records: Iterable[tuple[PerformanceSnapshot, AnalysisSnapshot]],
    *,
    dimension: CohortDimension,
    horizon: PerformanceHorizon,
    cohort_labels: Mapping[str, str | None] | None = None,
) -> tuple[CohortStatistics, ...]:
    grouped: dict[str, list[tuple[PerformanceSnapshot, AnalysisSnapshot]]] = {}
    for performance, analysis in records:
        if performance.analysis_snapshot_id != analysis.snapshot_id:
            raise ValueError("performance must be paired with its historical analysis snapshot")
        if performance.ticker != analysis.ticker:
            raise ValueError("performance ticker must match its historical analysis snapshot")
        key = _cohort_key(analysis, dimension)
        if cohort_labels is not None and analysis.snapshot_id in cohort_labels:
            key = cohort_labels[analysis.snapshot_id] or "unresolved"
        grouped.setdefault(key, []).append((performance, analysis))

    results: list[CohortStatistics] = []
    for cohort, items in sorted(grouped.items()):
        latest_by_analysis: dict[str, tuple[PerformanceSnapshot, AnalysisSnapshot]] = {}
        for performance, analysis in items:
            existing = latest_by_analysis.get(analysis.snapshot_id)
            candidate_horizon = next(item for item in performance.horizons if item.horizon == horizon)
            existing_horizon = (next(item for item in existing[0].horizons if item.horizon == horizon)
                                if existing is not None else None)
            candidate_key = (
                candidate_horizon.state == ResolutionState.RESOLVED,
                performance.evaluation_as_of,
                performance.created_at,
                performance.performance_snapshot_id,
            )
            existing_key = (
                existing_horizon.state == ResolutionState.RESOLVED,
                existing[0].evaluation_as_of,
                existing[0].created_at,
                existing[0].performance_snapshot_id,
            ) if existing is not None else None
            if existing_key is None or candidate_key > existing_key:
                latest_by_analysis[analysis.snapshot_id] = (performance, analysis)
        latest_items = tuple(latest_by_analysis.values())
        horizon_items = [
            next(item for item in performance.horizons if item.horizon == horizon)
            for performance, _analysis in latest_items
        ]
        returns = [
            item.stock_return for item in horizon_items
            if item.state == ResolutionState.RESOLVED and item.stock_return is not None
        ]
        alphas = [item.alpha for item in horizon_items if item.alpha is not None]
        drawdowns = [
            performance.max_drawdown for performance, _analysis in latest_items
            if performance.max_drawdown is not None
        ]
        mean_return, median_return = _stats(returns)
        mean_alpha, median_alpha = _stats(alphas)
        mean_drawdown, median_drawdown = _stats(drawdowns)
        results.append(CohortStatistics(
            dimension=dimension,
            cohort=cohort,
            horizon=horizon,
            evaluation_snapshot_count=len(items),
            snapshot_count=len(latest_items),
            return_sample_count=len(returns),
            mean_return=mean_return,
            median_return=median_return,
            minimum_return=min(returns) if returns else None,
            maximum_return=max(returns) if returns else None,
            positive_return_rate=(sum(value > 0 for value in returns) / len(returns)) if returns else None,
            alpha_sample_count=len(alphas),
            mean_alpha=mean_alpha,
            median_alpha=median_alpha,
            drawdown_sample_count=len(drawdowns),
            mean_max_drawdown=mean_drawdown,
            median_max_drawdown=median_drawdown,
        ))
    return tuple(results)
