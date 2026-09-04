from datetime import date, datetime, timedelta, timezone

import pytest

from engine.models import Grade
from engine.performance_engine import (
    add_calendar_months,
    build_performance_snapshot,
    calculate_max_drawdown,
    calculate_return,
)
from engine.tracking_models import (
    AlphaComparisonIssue,
    AnalysisCase,
    AnalysisSnapshot,
    BenchmarkAssignment,
    MetricResult,
    PerformanceHorizon,
    PerformanceReturnType,
    PriceBasis,
    PriceSeriesCoverageStatus,
    PriceSnapshot,
    PriceType,
    QuantSnapshot,
    ResolutionState,
)


UTC = timezone.utc


def analysis(start: datetime, reference_id="stock-start"):
    quant = QuantSnapshot(
        snapshot_id="quant",
        ticker="STOCK",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        model_version="case1-v1-frozen",
        metrics=(MetricResult(name="quality", state=ResolutionState.RESOLVED, value=1, grade=Grade.A, weight=1.0),),
        state=ResolutionState.RESOLVED,
        score=4.0,
        grade=Grade.A,
        period_end=start.date(),
        available_at=start,
        as_of=start,
    )
    return AnalysisSnapshot(
        snapshot_id="analysis",
        ticker="STOCK",
        company_name="Stock Company",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        case_definition_version="case1-v1-frozen",
        quant=quant,
        reference_price_snapshot_id=reference_id,
        period_end=start.date(),
        available_at=start,
        as_of=start,
    )


def price(identifier, ticker, timestamp, value, *, basis=PriceBasis.SPLIT_ADJUSTED, version="v1"):
    return PriceSnapshot(
        price_snapshot_id=identifier,
        ticker=ticker,
        timestamp=timestamp,
        price=value,
        currency="USD",
        source="offline fixture",
        price_type=PriceType.CLOSE,
        price_basis=basis,
        adjustment_version=version,
        provider_reference="synthetic corporate-action-safe series",
        created_at=timestamp + timedelta(minutes=1),
    )


def horizon(snapshot, key):
    return next(item for item in snapshot.horizons if item.horizon == key)


def build(start, prices, evaluation, **kwargs):
    return build_performance_snapshot(
        performance_snapshot_id=kwargs.pop("performance_snapshot_id", "performance"),
        analysis=analysis(start),
        instrument_id="stock-instrument",
        evaluation_as_of=evaluation,
        return_type=kwargs.pop("return_type", PerformanceReturnType.PRICE_RETURN),
        price_basis=kwargs.pop("price_basis", PriceBasis.SPLIT_ADJUSTED),
        stock_prices=prices,
        created_at=evaluation + timedelta(minutes=1),
        **kwargs,
    )


def test_calendar_horizon_month_end_and_exact_one_month_match():
    start = datetime(2026, 1, 31, 21, tzinfo=UTC)
    assert add_calendar_months(start.date(), 3) == date(2026, 4, 30)
    prices = (price("stock-start", "STOCK", start, 100), price("one-month", "STOCK", datetime(2026, 2, 28, 21, tzinfo=UTC), 110))
    result = build(start, prices, datetime(2026, 3, 1, tzinfo=UTC))
    one_month = horizon(result, PerformanceHorizon.ONE_MONTH)
    assert one_month.state == ResolutionState.RESOLVED
    assert one_month.stock_return == pytest.approx(0.10)


def test_weekend_target_uses_next_available_price_within_tolerance():
    start = datetime(2026, 1, 31, 21, tzinfo=UTC)
    monday = datetime(2026, 3, 2, 21, tzinfo=UTC)
    result = build(start, (price("stock-start", "STOCK", start, 100), price("monday", "STOCK", monday, 105)), monday)
    assert horizon(result, PerformanceHorizon.ONE_MONTH).end_price_snapshot_id == "monday"


def test_missing_within_tolerance_and_future_horizons_remain_unresolved():
    start = datetime(2026, 1, 31, 21, tzinfo=UTC)
    too_late = datetime(2026, 3, 10, 21, tzinfo=UTC)
    result = build(start, (price("stock-start", "STOCK", start, 100), price("late", "STOCK", too_late, 110)), too_late, horizon_tolerance_days=7)
    assert horizon(result, PerformanceHorizon.ONE_MONTH).state == ResolutionState.UNRESOLVED
    assert horizon(result, PerformanceHorizon.THREE_MONTHS).stock_return is None
    assert result.coverage == 0


@pytest.mark.parametrize(("start_price", "end_price", "expected"), ((100, 120, 0.20), (100, 80, -0.20), (100, 100, 0.0)))
def test_gain_loss_and_zero_return(start_price, end_price, expected):
    assert calculate_return(start_price, end_price) == pytest.approx(expected)


def test_split_adjusted_and_total_return_basis_contracts():
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    end = datetime(2026, 2, 1, 21, tzinfo=UTC)
    split_prices = (price("stock-start", "STOCK", start, 50), price("split-end", "STOCK", end, 55))
    split_result = build(start, split_prices, end)
    assert horizon(split_result, PerformanceHorizon.ONE_MONTH).stock_return == pytest.approx(0.10)
    total_prices = tuple(item.model_copy(update={"price_basis": PriceBasis.TOTAL_RETURN_ADJUSTED}) for item in split_prices)
    total_result = build(start, total_prices, end, price_basis=PriceBasis.TOTAL_RETURN_ADJUSTED, return_type=PerformanceReturnType.TOTAL_RETURN)
    assert horizon(total_result, PerformanceHorizon.ONE_MONTH).stock_return == pytest.approx(0.10)


def test_raw_split_scenario_is_unresolved_while_adjusted_series_is_zero():
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    end = datetime(2026, 2, 1, 21, tzinfo=UTC)
    raw_prices = (price("stock-start", "STOCK", start, 100, basis=PriceBasis.RAW), price("raw-end", "STOCK", end, 50, basis=PriceBasis.RAW))
    raw_result = build(start, raw_prices, end, price_basis=PriceBasis.RAW)
    assert raw_result.state == ResolutionState.UNRESOLVED
    assert horizon(raw_result, PerformanceHorizon.ONE_MONTH).stock_return is None
    assert raw_result.max_drawdown is None
    assert raw_result.mdd_coverage.status == PriceSeriesCoverageStatus.UNRESOLVED
    adjusted_prices = (price("stock-start", "STOCK", start, 50), price("adjusted-end", "STOCK", end, 50))
    adjusted_result = build(start, adjusted_prices, end)
    assert horizon(adjusted_result, PerformanceHorizon.ONE_MONTH).stock_return == 0


def test_missing_exact_analysis_reference_price_is_unresolved():
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    result = build_performance_snapshot(
        performance_snapshot_id="missing-reference",
        analysis=analysis(start, reference_id="not-in-series"),
        instrument_id="stock-instrument",
        evaluation_as_of=datetime(2026, 2, 1, 21, tzinfo=UTC),
        return_type=PerformanceReturnType.PRICE_RETURN,
        price_basis=PriceBasis.SPLIT_ADJUSTED,
        stock_prices=(price("arbitrary-earlier", "STOCK", start - timedelta(days=1), 99),),
        created_at=datetime(2026, 2, 1, 22, tzinfo=UTC),
    )
    assert result.state == ResolutionState.UNRESOLVED
    assert result.start_price_snapshot_id is None


def test_drawdown_known_paths_and_dense_adjusted_series():
    assert calculate_max_drawdown((100, 110, 120)) == 0
    assert calculate_max_drawdown((100, 120, 90)) == pytest.approx(-0.25)
    assert calculate_max_drawdown((100, 120, 90, 130)) == pytest.approx(-0.25)
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    prices = tuple(price("stock-start" if day == 0 else f"day-{day}", "STOCK", start + timedelta(days=day), 100 + day) for day in range(9))
    result = build(start, prices, start + timedelta(days=8))
    assert result.max_drawdown == 0
    assert result.mdd_coverage.status == PriceSeriesCoverageStatus.SUFFICIENT


@pytest.mark.parametrize(("gap", "expected"), ((7, PriceSeriesCoverageStatus.SUFFICIENT), (8, PriceSeriesCoverageStatus.INSUFFICIENT)))
def test_mdd_maximum_gap_boundary(gap, expected):
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    result = build(start, (price("stock-start", "STOCK", start, 100), price("end", "STOCK", start + timedelta(days=gap), 90)), start + timedelta(days=gap))
    assert result.mdd_coverage.maximum_observed_gap_days == gap
    assert result.mdd_coverage.status == expected
    assert (result.max_drawdown is not None) == (expected == PriceSeriesCoverageStatus.SUFFICIENT)


def test_sparse_and_missing_evaluation_end_mdd_are_unresolved():
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    sparse = build(start, (price("stock-start", "STOCK", start, 100), price("end", "STOCK", start + timedelta(days=9), 90)), start + timedelta(days=9))
    assert sparse.max_drawdown is None
    assert sparse.mdd_coverage.status == PriceSeriesCoverageStatus.INSUFFICIENT
    stale_prices = tuple(price("stock-start" if day == 0 else f"stale-{day}", "STOCK", start + timedelta(days=day), 100) for day in range(3))
    stale = build(start, stale_prices, start + timedelta(days=10))
    assert stale.max_drawdown is None
    assert "evaluation period" in stale.mdd_coverage.reason


def test_benchmark_return_alpha_and_missing_benchmark_independence():
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    end = datetime(2026, 2, 1, 21, tzinfo=UTC)
    stock = (price("stock-start", "STOCK", start, 100), price("stock-end", "STOCK", end, 120))
    benchmark = (price("benchmark-start", "BENCH", start, 200), price("benchmark-end", "BENCH", end, 220))
    assignment = BenchmarkAssignment(assignment_id="benchmark", instrument_id="stock-instrument", benchmark_instrument_id="benchmark-instrument", version=1, valid_from=start - timedelta(days=1), rationale="explicit benchmark", created_at=start)
    compared = build(start, stock, end, benchmark_assignment=assignment, benchmark_prices=benchmark, benchmark_start_price_snapshot_id="benchmark-start")
    one_month = horizon(compared, PerformanceHorizon.ONE_MONTH)
    assert one_month.benchmark_return == pytest.approx(0.10)
    assert one_month.alpha == pytest.approx(0.10)
    assert one_month.alpha_state == ResolutionState.RESOLVED
    stock_only = build(start, stock, end, performance_snapshot_id="stock-only", benchmark_assignment=assignment)
    assert horizon(stock_only, PerformanceHorizon.ONE_MONTH).stock_return == pytest.approx(0.20)
    assert horizon(stock_only, PerformanceHorizon.ONE_MONTH).alpha is None
    assert stock_only.benchmark_assignment_id == assignment.assignment_id
    assert stock_only.benchmark_start_price_snapshot_id is None


@pytest.mark.parametrize(
    ("stock_basis", "stock_type", "benchmark_basis", "benchmark_type"),
    (
        (PriceBasis.SPLIT_ADJUSTED, PerformanceReturnType.PRICE_RETURN, PriceBasis.SPLIT_ADJUSTED, PerformanceReturnType.PRICE_RETURN),
        (PriceBasis.TOTAL_RETURN_ADJUSTED, PerformanceReturnType.TOTAL_RETURN, PriceBasis.TOTAL_RETURN_ADJUSTED, PerformanceReturnType.TOTAL_RETURN),
    ),
)
def test_alpha_resolves_for_matching_return_types(stock_basis, stock_type, benchmark_basis, benchmark_type):
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    end = datetime(2026, 2, 1, 21, tzinfo=UTC)
    assignment = BenchmarkAssignment(assignment_id="benchmark", instrument_id="stock-instrument", benchmark_instrument_id="benchmark-instrument", version=1, valid_from=start, rationale="explicit", created_at=start)
    stock = (price("stock-start", "STOCK", start, 100, basis=stock_basis), price("stock-end", "STOCK", end, 120, basis=stock_basis))
    benchmark = (price("benchmark-start", "BENCH", start, 100, basis=benchmark_basis), price("benchmark-end", "BENCH", end, 110, basis=benchmark_basis))
    result = build(start, stock, end, price_basis=stock_basis, return_type=stock_type, benchmark_assignment=assignment, benchmark_prices=benchmark, benchmark_start_price_snapshot_id="benchmark-start", benchmark_price_basis=benchmark_basis, benchmark_return_type=benchmark_type)
    assert horizon(result, PerformanceHorizon.ONE_MONTH).alpha == pytest.approx(0.10)


def test_alpha_return_type_mismatch_preserves_both_returns():
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    end = datetime(2026, 2, 1, 21, tzinfo=UTC)
    assignment = BenchmarkAssignment(assignment_id="benchmark", instrument_id="stock-instrument", benchmark_instrument_id="benchmark-instrument", version=1, valid_from=start, rationale="explicit", created_at=start)
    stock = (price("stock-start", "STOCK", start, 100), price("stock-end", "STOCK", end, 120))
    benchmark = (price("benchmark-start", "BENCH", start, 100, basis=PriceBasis.TOTAL_RETURN_ADJUSTED), price("benchmark-end", "BENCH", end, 110, basis=PriceBasis.TOTAL_RETURN_ADJUSTED))
    result = build(start, stock, end, benchmark_assignment=assignment, benchmark_prices=benchmark, benchmark_start_price_snapshot_id="benchmark-start", benchmark_price_basis=PriceBasis.TOTAL_RETURN_ADJUSTED, benchmark_return_type=PerformanceReturnType.TOTAL_RETURN)
    item = horizon(result, PerformanceHorizon.ONE_MONTH)
    assert item.stock_return == pytest.approx(0.20)
    assert item.benchmark_return == pytest.approx(0.10)
    assert item.alpha is None
    assert item.alpha_unresolved_reason == AlphaComparisonIssue.RETURN_TYPE_MISMATCH


@pytest.mark.parametrize(("benchmark_start_offset", "benchmark_end_offset", "reason"), ((1, 1, AlphaComparisonIssue.START_DATE_MISMATCH), (0, 1, AlphaComparisonIssue.END_DATE_MISMATCH)))
def test_alpha_effective_date_mismatch_is_unresolved(benchmark_start_offset, benchmark_end_offset, reason):
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    end = datetime(2026, 2, 1, 21, tzinfo=UTC)
    assignment = BenchmarkAssignment(assignment_id="benchmark", instrument_id="stock-instrument", benchmark_instrument_id="benchmark-instrument", version=1, valid_from=start, rationale="explicit", created_at=start)
    stock = (price("stock-start", "STOCK", start, 100), price("stock-end", "STOCK", end, 120))
    benchmark = (price("benchmark-start", "BENCH", start + timedelta(days=benchmark_start_offset), 100), price("benchmark-end", "BENCH", end + timedelta(days=benchmark_end_offset), 110))
    result = build(start, stock, end + timedelta(days=benchmark_end_offset), benchmark_assignment=assignment, benchmark_prices=benchmark, benchmark_start_price_snapshot_id="benchmark-start")
    item = horizon(result, PerformanceHorizon.ONE_MONTH)
    assert item.stock_return == pytest.approx(0.20)
    assert item.benchmark_return == pytest.approx(0.10)
    assert item.alpha is None
    assert item.alpha_unresolved_reason == reason


def test_future_prices_are_downstream_only_and_analysis_is_unchanged():
    start = datetime(2026, 1, 1, 21, tzinfo=UTC)
    historical_analysis = analysis(start)
    before = historical_analysis.model_dump()
    result = build_performance_snapshot(performance_snapshot_id="future", analysis=historical_analysis, instrument_id="stock-instrument", evaluation_as_of=datetime(2026, 4, 1, 21, tzinfo=UTC), return_type=PerformanceReturnType.PRICE_RETURN, price_basis=PriceBasis.SPLIT_ADJUSTED, stock_prices=(price("stock-start", "STOCK", start, 100), price("future", "STOCK", datetime(2026, 4, 1, 21, tzinfo=UTC), 150)), created_at=datetime(2026, 4, 1, 22, tzinfo=UTC))
    assert result.return_since_analysis == pytest.approx(0.50)
    assert historical_analysis.model_dump() == before
