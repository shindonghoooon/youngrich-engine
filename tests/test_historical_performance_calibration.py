from datetime import datetime

import pytest

from engine.performance_analytics import CohortDimension, analyze_performance_cohorts
from engine.performance_engine import add_calendar_months, calculate_return
from engine.tracking_models import (
    AlphaComparisonIssue,
    InvestmentGrade,
    PerformanceHorizon,
    PriceBasis,
    PriceSeriesCoverageStatus,
    ResolutionState,
)
from research.historical_performance_calibration import (
    AnalysisInputState,
    load_historical_stress_records,
    research_cohort_labels,
)


@pytest.fixture(scope="module")
def records():
    return load_historical_stress_records()


def by_id(records, sample_id):
    return next(item for item in records if item.metadata.sample_id == sample_id)


def horizon(record, requested):
    return next(item for item in record.performance.horizons if item.horizon == requested)


def test_stress_basket_is_complete_and_historical_inputs_are_honestly_unresolved(records):
    assert len(records) == 13
    assert {item.metadata.sample_id for item in records} == {
        "adbe_fy2017", "adbe_fy2021", "pypl_fy2021", "nvda_fy2018",
        "pltr_fy2021", "crwd_fy2020", "net_fy2020", "shop_fy2015",
        "tsla_fy2014", "mdb_fy2020", "fsly_fy2021", "sklz_fy2021",
        "vldr_fy2020",
    }
    assert all(item.metadata.analysis_input_state == AnalysisInputState.ANALYSIS_INPUT_INCOMPLETE for item in records)
    assert all(item.analysis.quant.state == ResolutionState.UNRESOLVED for item in records)
    assert by_id(records, "nvda_fy2018").metadata.sample_role == "SUPPORTING_BOUNDARY"
    assert by_id(records, "vldr_fy2020").metadata.canonical_investment_grade is None
    assert by_id(records, "vldr_fy2020").metadata.canonical_grade_range == (InvestmentGrade.D, InvestmentGrade.X)


def test_sec_availability_and_reference_price_timing_are_point_in_time_safe(records):
    for record in records:
        assert record.analysis.available_at <= record.analysis.as_of
        assert record.metadata.information_available_at <= record.metadata.analysis_as_of
        source = record.raw_fixture["analysis_provenance"]
        assert source["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
        if record.raw_fixture["reference_price"] is not None:
            reference_at = datetime.fromisoformat(record.raw_fixture["reference_price"]["timestamp"].replace("Z", "+00:00"))
            assert reference_at > record.metadata.information_available_at
            assert record.analysis.reference_price_snapshot_id is not None


@pytest.mark.parametrize("sample_id", ("adbe_fy2017", "adbe_fy2021", "crwd_fy2020", "fsly_fy2021"))
def test_required_winner_and_failure_samples_resolve_offline(records, sample_id):
    record = by_id(records, sample_id)
    assert record.performance.price_basis == PriceBasis.SPLIT_ADJUSTED
    assert horizon(record, PerformanceHorizon.ONE_YEAR).state == ResolutionState.RESOLVED
    assert record.performance.mdd_coverage.status == PriceSeriesCoverageStatus.SUFFICIENT
    assert record.performance.max_drawdown is not None


def test_adbe_fy2017_horizon_return_mdd_and_alpha_reproduce_fixture_arithmetic(records):
    record = by_id(records, "adbe_fy2017")
    raw = record.raw_fixture
    start = raw["stock_prices"][0]
    one_year = horizon(record, PerformanceHorizon.ONE_YEAR)
    expected_end = next(
        item for item in raw["stock_prices"]
        if item["timestamp"][:10] == one_year.stock_end_effective_date.isoformat()
    )
    assert one_year.target_date == add_calendar_months(datetime.fromisoformat(start["timestamp"].replace("Z", "+00:00")).date(), 12)
    assert one_year.stock_return == pytest.approx(calculate_return(start["price"], expected_end["price"]))
    assert record.performance.return_since_analysis == pytest.approx(one_year.stock_return)
    assert record.performance.max_drawdown == pytest.approx(-0.25529053346886366)
    assert one_year.alpha_state == ResolutionState.RESOLVED
    assert one_year.alpha == pytest.approx(one_year.stock_return - one_year.benchmark_return)
    assert one_year.stock_start_effective_date == one_year.benchmark_start_effective_date
    assert one_year.stock_end_effective_date == one_year.benchmark_end_effective_date


def test_provider_unavailable_series_remain_unresolved_without_raw_fallback(records):
    for sample_id in ("sklz_fy2021", "vldr_fy2020"):
        record = by_id(records, sample_id)
        assert record.raw_fixture["price_source"]["error"]
        assert record.raw_fixture["stock_prices"] == []
        assert record.performance.state == ResolutionState.UNRESOLVED
        assert record.performance.max_drawdown is None
        assert record.performance.mdd_coverage.status == PriceSeriesCoverageStatus.UNRESOLVED
        assert all(item.alpha is None for item in record.performance.horizons)


def test_explicit_benchmark_assignments_and_comparable_alpha(records):
    resolved = [item for item in records if item.performance.state == ResolutionState.RESOLVED]
    assert resolved
    for record in resolved:
        assert record.performance.benchmark_assignment_id == f"{record.metadata.sample_id}-benchmark-assignment"
        assert record.performance.benchmark_instrument_id == "spy-instrument"
        item = horizon(record, PerformanceHorizon.ONE_YEAR)
        assert record.performance.return_since_analysis == pytest.approx(item.stock_return)
        assert item.alpha_unresolved_reason is None
        assert item.alpha_state == ResolutionState.RESOLVED
    unresolved = by_id(records, "sklz_fy2021")
    assert all(item.alpha_unresolved_reason in (None, AlphaComparisonIssue.BENCHMARK_UNAVAILABLE) for item in unresolved.performance.horizons)


def test_actual_cohort_analytics_preserve_counts_and_research_unknowns(records):
    pairs = tuple((item.performance, item.analysis) for item in records)
    grades = {item.cohort: item for item in analyze_performance_cohorts(
        pairs, dimension=CohortDimension.INVESTMENT_GRADE, horizon=PerformanceHorizon.ONE_YEAR
    )}
    assert grades["B"].snapshot_count == 6 and grades["B"].return_sample_count == 6
    assert grades["C"].snapshot_count == 3 and grades["C"].return_sample_count == 3
    assert grades["D"].snapshot_count == 3 and grades["D"].return_sample_count == 2
    assert grades["unresolved"].snapshot_count == 1 and grades["unresolved"].return_sample_count == 0
    gaps = {item.cohort: item for item in analyze_performance_cohorts(
        pairs, dimension=CohortDimension.EXPECTATION_GAP,
        horizon=PerformanceHorizon.ONE_YEAR,
        cohort_labels=research_cohort_labels(records, "expectation_gap"),
    )}
    assert gaps["negative"].snapshot_count == 1
    assert gaps["unresolved"].snapshot_count == 12
    funding = analyze_performance_cohorts(
        pairs, dimension=CohortDimension.FUNDING_STRESS,
        horizon=PerformanceHorizon.ONE_YEAR,
        cohort_labels=research_cohort_labels(records, "funding_stress"),
    )
    assert len(funding) == 1 and funding[0].cohort == "unresolved"
