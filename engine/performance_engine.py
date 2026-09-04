"""Pure downstream evaluation of analysis-signal market performance."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from engine.tracking_models import (
    AlphaComparisonIssue, AnalysisSnapshot, BenchmarkAssignment, HorizonPerformance,
    PerformanceHorizon, PerformanceReturnType, PerformanceSnapshot, PriceBasis,
    PriceSeriesCoverage, PriceSeriesCoverageStatus, PriceSnapshot, ResolutionState,
)

PERFORMANCE_CALCULATION_VERSION = "performance-v1"
DEFAULT_HORIZON_TOLERANCE_DAYS = 7
DEFAULT_MDD_MAX_GAP_DAYS = 7
HORIZON_MONTHS = {
    PerformanceHorizon.ONE_MONTH: 1, PerformanceHorizon.THREE_MONTHS: 3,
    PerformanceHorizon.SIX_MONTHS: 6, PerformanceHorizon.ONE_YEAR: 12,
}


def add_calendar_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def calculate_return(start_price: float, end_price: float) -> float:
    if start_price <= 0 or end_price <= 0:
        raise ValueError("performance prices must be positive")
    return end_price / start_price - 1.0


def calculate_max_drawdown(prices: Iterable[float]) -> float | None:
    values = tuple(prices)
    if not values:
        return None
    if any(value <= 0 for value in values):
        raise ValueError("drawdown prices must be positive")
    peak = values[0]
    result = 0.0
    for value in values:
        peak = max(peak, value)
        result = min(result, value / peak - 1.0)
    return result


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _series_for_basis(prices: Iterable[PriceSnapshot], *, basis: PriceBasis,
                      adjustment_version: str | None,
                      evaluation_as_of: datetime) -> tuple[PriceSnapshot, ...]:
    return tuple(sorted((item for item in prices
                         if item.price_basis == basis
                         and item.adjustment_version == adjustment_version
                         and item.timestamp <= evaluation_as_of),
                        key=lambda item: (item.timestamp, item.price_snapshot_id)))


def resolve_horizon_price(prices: Iterable[PriceSnapshot], *, target_date: date,
                          evaluation_as_of: datetime,
                          tolerance_days: int = DEFAULT_HORIZON_TOLERANCE_DAYS) -> PriceSnapshot | None:
    if tolerance_days < 0:
        raise ValueError("horizon_tolerance_days cannot be negative")
    if target_date > evaluation_as_of.date():
        return None
    latest_date = target_date + timedelta(days=tolerance_days)
    eligible = (item for item in prices
                if target_date <= item.timestamp.date() <= latest_date
                and item.timestamp <= evaluation_as_of)
    return min(eligible, key=lambda item: (item.timestamp, item.price_snapshot_id), default=None)


def evaluate_mdd_coverage(prices: Iterable[PriceSnapshot], *,
                          analysis_start: PriceSnapshot | None,
                          evaluation_as_of: datetime, price_basis: PriceBasis,
                          mdd_max_gap_days: int = DEFAULT_MDD_MAX_GAP_DAYS,
                          evaluation_end_tolerance_days: int = DEFAULT_HORIZON_TOLERANCE_DAYS,
                          ) -> PriceSeriesCoverage:
    """Apply the v1 calendar-day approximation for adjustment-safe MDD coverage."""
    if mdd_max_gap_days < 0 or evaluation_end_tolerance_days < 0:
        raise ValueError("MDD coverage tolerances cannot be negative")
    observed = tuple(sorted(prices, key=lambda item: (item.timestamp, item.price_snapshot_id)))
    first = observed[0].timestamp if observed else None
    last = observed[-1].timestamp if observed else None
    max_gap = (max((current.timestamp.date() - previous.timestamp.date()).days
                   for previous, current in zip(observed, observed[1:]))
               if len(observed) >= 2 else None)

    def result(status: PriceSeriesCoverageStatus, reason: str | None) -> PriceSeriesCoverage:
        return PriceSeriesCoverage(status=status, observation_count=len(observed),
                                   first_timestamp=first, last_timestamp=last,
                                   maximum_observed_gap_days=max_gap, reason=reason)

    if price_basis == PriceBasis.RAW:
        return result(PriceSeriesCoverageStatus.UNRESOLVED, "raw price series is not adjustment-safe")
    if analysis_start is None:
        return result(PriceSeriesCoverageStatus.UNRESOLVED, "exact analysis start price is unavailable")
    if len(observed) < 2:
        return result(PriceSeriesCoverageStatus.INSUFFICIENT, "at least two price observations are required")
    if observed[0].price_snapshot_id != analysis_start.price_snapshot_id:
        return result(PriceSeriesCoverageStatus.INSUFFICIENT, "first observation does not cover the exact analysis start")
    if (evaluation_as_of.date() - observed[-1].timestamp.date()).days > evaluation_end_tolerance_days:
        return result(PriceSeriesCoverageStatus.INSUFFICIENT, "price series does not reach the evaluation period")
    if max_gap is not None and max_gap > mdd_max_gap_days:
        return result(PriceSeriesCoverageStatus.INSUFFICIENT, "maximum observed gap exceeds mdd_max_gap_days")
    return result(PriceSeriesCoverageStatus.SUFFICIENT, None)


def _empty_horizons(start_date: date) -> tuple[HorizonPerformance, ...]:
    return tuple(HorizonPerformance(horizon=horizon, state=ResolutionState.UNRESOLVED,
                                    target_date=add_calendar_months(start_date, months))
                 for horizon, months in HORIZON_MONTHS.items())


def _unresolved_snapshot(*, performance_snapshot_id: str, analysis: AnalysisSnapshot,
                         instrument_id: str, evaluation_as_of: datetime,
                         return_type: PerformanceReturnType, price_basis: PriceBasis,
                         created_at: datetime, note: str,
                         mdd_coverage: PriceSeriesCoverage) -> PerformanceSnapshot:
    return PerformanceSnapshot(
        performance_snapshot_id=performance_snapshot_id, ticker=analysis.ticker,
        analysis_snapshot_id=analysis.snapshot_id, instrument_id=instrument_id,
        evaluation_as_of=evaluation_as_of.astimezone(timezone.utc), return_type=return_type,
        price_basis=price_basis, horizons=_empty_horizons(analysis.as_of.date()),
        mdd_coverage=mdd_coverage, state=ResolutionState.UNRESOLVED, coverage=0.0,
        calculation_version=PERFORMANCE_CALCULATION_VERSION,
        created_at=created_at.astimezone(timezone.utc), note=note)


def build_performance_snapshot(*, performance_snapshot_id: str, analysis: AnalysisSnapshot,
                               instrument_id: str, evaluation_as_of: datetime,
                               return_type: PerformanceReturnType, price_basis: PriceBasis,
                               stock_prices: Iterable[PriceSnapshot], created_at: datetime,
                               horizon_tolerance_days: int = DEFAULT_HORIZON_TOLERANCE_DAYS,
                               mdd_max_gap_days: int = DEFAULT_MDD_MAX_GAP_DAYS,
                               benchmark_assignment: BenchmarkAssignment | None = None,
                               benchmark_prices: Iterable[PriceSnapshot] = (),
                               benchmark_start_price_snapshot_id: str | None = None,
                               benchmark_return_type: PerformanceReturnType | None = None,
                               benchmark_price_basis: PriceBasis | None = None) -> PerformanceSnapshot:
    """Evaluate future prices without mutating or feeding back into the analysis."""
    _require_aware(evaluation_as_of, "evaluation_as_of")
    _require_aware(created_at, "created_at")
    if evaluation_as_of < analysis.as_of:
        raise ValueError("performance evaluation cannot precede analysis as_of")
    if horizon_tolerance_days < 0 or mdd_max_gap_days < 0:
        raise ValueError("performance tolerances cannot be negative")
    all_stock_prices = tuple(stock_prices)
    if any(item.ticker != analysis.ticker for item in all_stock_prices):
        raise ValueError("stock price series ticker must match the historical analysis")
    empty_mdd = evaluate_mdd_coverage((), analysis_start=None,
                                      evaluation_as_of=evaluation_as_of,
                                      price_basis=price_basis,
                                      mdd_max_gap_days=mdd_max_gap_days,
                                      evaluation_end_tolerance_days=horizon_tolerance_days)

    def unresolved(note: str) -> PerformanceSnapshot:
        return _unresolved_snapshot(performance_snapshot_id=performance_snapshot_id,
                                    analysis=analysis, instrument_id=instrument_id,
                                    evaluation_as_of=evaluation_as_of, return_type=return_type,
                                    price_basis=price_basis, created_at=created_at, note=note,
                                    mdd_coverage=empty_mdd)

    if price_basis == PriceBasis.RAW:
        return unresolved("raw price series is not corporate-action-safe")
    expected_type = {PriceBasis.SPLIT_ADJUSTED: PerformanceReturnType.PRICE_RETURN,
                     PriceBasis.TOTAL_RETURN_ADJUSTED: PerformanceReturnType.TOTAL_RETURN}[price_basis]
    if return_type != expected_type:
        return unresolved("return type does not match the adjusted price basis")
    if analysis.reference_price_snapshot_id is None:
        return unresolved("analysis has no exact reference PriceSnapshot")
    start = next((item for item in all_stock_prices
                  if item.price_snapshot_id == analysis.reference_price_snapshot_id), None)
    if start is None or start.price_basis != price_basis or start.timestamp > evaluation_as_of:
        return unresolved("referenced start price is unavailable, incompatible, or after evaluation")
    stock_series = _series_for_basis(all_stock_prices, basis=price_basis,
                                     adjustment_version=start.adjustment_version,
                                     evaluation_as_of=evaluation_as_of)
    stock_series = tuple(item for item in stock_series if item.timestamp >= start.timestamp)

    benchmark_type = benchmark_return_type or return_type
    benchmark_basis = benchmark_price_basis or price_basis
    benchmark_start = None
    benchmark_series: tuple[PriceSnapshot, ...] = ()
    if benchmark_assignment is not None:
        if benchmark_assignment.instrument_id != instrument_id:
            raise ValueError("benchmark assignment instrument must match performance instrument")
        if benchmark_assignment.valid_from > analysis.as_of:
            raise ValueError("benchmark assignment cannot take effect after analysis as_of")
        if benchmark_start_price_snapshot_id is not None:
            all_benchmark_prices = tuple(benchmark_prices)
            benchmark_start = next((item for item in all_benchmark_prices
                                    if item.price_snapshot_id == benchmark_start_price_snapshot_id), None)
            if benchmark_start is not None and benchmark_start.price_basis == benchmark_basis:
                if any(item.ticker != benchmark_start.ticker for item in all_benchmark_prices):
                    raise ValueError("benchmark price series must contain one ticker")
                benchmark_series = _series_for_basis(all_benchmark_prices, basis=benchmark_basis,
                                                     adjustment_version=benchmark_start.adjustment_version,
                                                     evaluation_as_of=evaluation_as_of)
                benchmark_series = tuple(item for item in benchmark_series
                                         if item.timestamp >= benchmark_start.timestamp)
            else:
                benchmark_start = None

    horizons: list[HorizonPerformance] = []
    for horizon, months in HORIZON_MONTHS.items():
        target_date = add_calendar_months(start.timestamp.date(), months)
        end = resolve_horizon_price(stock_series, target_date=target_date,
                                    evaluation_as_of=evaluation_as_of,
                                    tolerance_days=horizon_tolerance_days)
        if end is None:
            horizons.append(HorizonPerformance(horizon=horizon, state=ResolutionState.UNRESOLVED,
                                                target_date=target_date,
                                                stock_start_effective_date=start.timestamp.date()))
            continue
        stock_return = calculate_return(start.price, end.price)
        benchmark_values: dict[str, object] = {}
        alpha_state = ResolutionState.UNRESOLVED
        alpha_reason = AlphaComparisonIssue.BENCHMARK_UNAVAILABLE if benchmark_assignment else None
        if benchmark_start is not None:
            benchmark_target = add_calendar_months(benchmark_start.timestamp.date(), months)
            benchmark_end = resolve_horizon_price(benchmark_series, target_date=benchmark_target,
                                                  evaluation_as_of=evaluation_as_of,
                                                  tolerance_days=horizon_tolerance_days)
            if benchmark_end is not None:
                benchmark_return = calculate_return(benchmark_start.price, benchmark_end.price)
                benchmark_values = {
                    "benchmark_end_price_snapshot_id": benchmark_end.price_snapshot_id,
                    "benchmark_end_price": benchmark_end.price,
                    "benchmark_return": benchmark_return,
                    "benchmark_return_type": benchmark_type,
                    "benchmark_start_effective_date": benchmark_start.timestamp.date(),
                    "benchmark_end_effective_date": benchmark_end.timestamp.date(),
                }
                if return_type != benchmark_type:
                    alpha_reason = AlphaComparisonIssue.RETURN_TYPE_MISMATCH
                elif start.timestamp.date() != benchmark_start.timestamp.date():
                    alpha_reason = AlphaComparisonIssue.START_DATE_MISMATCH
                elif end.timestamp.date() != benchmark_end.timestamp.date():
                    alpha_reason = AlphaComparisonIssue.END_DATE_MISMATCH
                else:
                    alpha_state = ResolutionState.RESOLVED
                    alpha_reason = None
                    benchmark_values["alpha"] = stock_return - benchmark_return
        horizons.append(HorizonPerformance(
            horizon=horizon, state=ResolutionState.RESOLVED, target_date=target_date,
            end_price_snapshot_id=end.price_snapshot_id, end_price=end.price,
            stock_return=stock_return, stock_start_effective_date=start.timestamp.date(),
            stock_end_effective_date=end.timestamp.date(), alpha_state=alpha_state,
            alpha_unresolved_reason=alpha_reason, **benchmark_values))

    latest = stock_series[-1] if stock_series else None
    if latest is not None and (evaluation_as_of.date() - latest.timestamp.date()).days > horizon_tolerance_days:
        latest = None
    since_analysis = calculate_return(start.price, latest.price) if latest else None
    mdd_coverage = evaluate_mdd_coverage(stock_series, analysis_start=start,
                                         evaluation_as_of=evaluation_as_of,
                                         price_basis=price_basis,
                                         mdd_max_gap_days=mdd_max_gap_days,
                                         evaluation_end_tolerance_days=horizon_tolerance_days)
    max_drawdown = (calculate_max_drawdown(item.price for item in stock_series)
                    if mdd_coverage.status == PriceSeriesCoverageStatus.SUFFICIENT else None)
    coverage = sum(item.state == ResolutionState.RESOLVED for item in horizons) / len(HORIZON_MONTHS)
    return PerformanceSnapshot(
        performance_snapshot_id=performance_snapshot_id, ticker=analysis.ticker,
        analysis_snapshot_id=analysis.snapshot_id, instrument_id=instrument_id,
        evaluation_as_of=evaluation_as_of.astimezone(timezone.utc), return_type=return_type,
        price_basis=price_basis, start_price_snapshot_id=start.price_snapshot_id,
        start_price=start.price,
        benchmark_assignment_id=benchmark_assignment.assignment_id if benchmark_assignment else None,
        benchmark_assignment_version=benchmark_assignment.version if benchmark_assignment else None,
        benchmark_instrument_id=benchmark_assignment.benchmark_instrument_id if benchmark_assignment else None,
        benchmark_return_type=benchmark_type if benchmark_assignment else None,
        benchmark_price_basis=benchmark_basis if benchmark_assignment else None,
        benchmark_start_price_snapshot_id=benchmark_start.price_snapshot_id if benchmark_start else None,
        benchmark_start_price=benchmark_start.price if benchmark_start else None,
        horizons=tuple(horizons), return_since_analysis=since_analysis,
        max_drawdown=max_drawdown, mdd_coverage=mdd_coverage, state=ResolutionState.RESOLVED,
        coverage=coverage, calculation_version=PERFORMANCE_CALCULATION_VERSION,
        created_at=created_at.astimezone(timezone.utc),
        note=(None if mdd_coverage.status == PriceSeriesCoverageStatus.SUFFICIENT
              else f"max drawdown unresolved: {mdd_coverage.reason}"))
