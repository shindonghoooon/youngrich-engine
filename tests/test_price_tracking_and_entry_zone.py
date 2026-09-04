from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from engine.entry_zone import case1_entry_zone, case2_entry_zone
from engine.price_tracking import compare_prices
from engine.tracking_models import (
    AnalysisCase,
    AssumptionRange,
    ExitMultipleAssumption,
    ExitMultipleBand,
    ExitMultipleEvidenceSource,
    PriceSnapshot,
    PriceType,
    TerminalStage,
    ValuationAssumptionSet,
    ValuationConfidence,
    ValuationMetric,
)


UTC = timezone.utc
NOW = datetime(2026, 9, 1, 20, tzinfo=UTC)


def price(identifier, timestamp, value, *, market_cap=None, enterprise_value=None):
    return PriceSnapshot(
        price_snapshot_id=identifier,
        ticker="TEST",
        company_id="company-test",
        timestamp=timestamp,
        price=value,
        currency="USD",
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        source="manual official close fixture",
        price_type=PriceType.CLOSE,
        created_at=timestamp + timedelta(minutes=5),
    )


def multiples(metric, values=(4.0, 5.0, 6.0)):
    return tuple(
        ExitMultipleAssumption(
            band=band,
            metric_type=metric,
            value=value,
            evidence_type=ExitMultipleEvidenceSource.COMPARABLE_COMPANIES,
            source_reference="synthetic evidence",
            as_of=NOW,
            rationale="reverse-formula test",
        )
        for band, value in zip(ExitMultipleBand, values, strict=True)
    )


def case2_assumptions(metric=ValuationMetric.EV_REVENUE, *, stage=TerminalStage.GROWTH, dilution=0.05, version=3):
    return ValuationAssumptionSet(
        assumption_set_id="case2-entry",
        version=version,
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        horizon_years=5,
        terminal_stage=stage,
        terminal_stage_rationale="synthetic terminal state",
        terminal_stage_confidence=ValuationConfidence.MEDIUM,
        primary_metric=metric,
        exit_multiples=multiples(metric),
        plausible_growth_range=AssumptionRange(low=0.20, high=0.40),
        expected_annual_dilution=dilution,
        target_gross_margin=0.50 if metric == ValuationMetric.EV_GROSS_PROFIT else None,
        target_operating_margin=0.20 if metric == ValuationMetric.EV_EBIT else None,
        terminal_net_debt=10,
    )


def test_price_snapshot_is_immutable_and_rejects_invalid_price():
    snapshot = price("p1", NOW, 10)
    with pytest.raises(ValidationError, match="frozen"):
        snapshot.price = 11
    for invalid in (0, -1):
        with pytest.raises(ValidationError):
            price("bad", NOW, invalid)
    net_cash_company = price("negative-ev", NOW, 10, market_cap=100, enterprise_value=-20)
    assert net_cash_company.enterprise_value == -20


def test_price_snapshot_and_comparison_chronology():
    with pytest.raises(ValidationError, match="created_at cannot precede"):
        PriceSnapshot(price_snapshot_id="bad-time", ticker="TEST", timestamp=NOW, price=10, currency="USD", source="fixture", price_type=PriceType.EOD, created_at=NOW - timedelta(seconds=1))
    with pytest.raises(ValueError, match="later"):
        compare_prices(price("p1", NOW, 10), price("p2", NOW, 11))


@pytest.mark.parametrize(
    ("timestamp", "created_at", "message"),
    (
        (NOW.replace(tzinfo=None), NOW, "timestamp must be timezone-aware"),
        (NOW, NOW.replace(tzinfo=None), "created_at must be timezone-aware"),
    ),
)
def test_price_snapshot_rejects_naive_datetimes(timestamp, created_at, message):
    with pytest.raises(ValidationError, match=message):
        PriceSnapshot(
            price_snapshot_id="naive",
            ticker="TEST",
            timestamp=timestamp,
            price=10,
            currency="USD",
            source="fixture",
            price_type=PriceType.EOD,
            created_at=created_at,
        )


def test_price_tracking_positive_negative_and_enterprise_changes():
    previous = price("p1", NOW, 10, market_cap=100, enterprise_value=120)
    higher = price("p2", NOW + timedelta(days=1), 12, market_cap=120, enterprise_value=138)
    lower = price("p3", NOW + timedelta(days=2), 9, market_cap=90, enterprise_value=105)
    gain = compare_prices(previous, higher)
    loss = compare_prices(higher, lower)
    assert gain.absolute_change == 2
    assert gain.return_ratio == pytest.approx(0.20)
    assert gain.market_cap_change == 20
    assert gain.enterprise_value_change == 18
    assert loss.return_ratio == pytest.approx(-0.25)


def test_case1_reverse_formula_known_example_and_version():
    assumptions = ValuationAssumptionSet(
        assumption_set_id="case1-entry", version=7, case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        horizon_years=3, terminal_stage=TerminalStage.MATURE, terminal_stage_rationale="test",
        terminal_stage_confidence=ValuationConfidence.MEDIUM, primary_metric=ValuationMetric.PE,
        exit_multiples=multiples(ValuationMetric.PE, (12, 16, 20)), plausible_growth_range=AssumptionRange(low=0.10, high=0.20),
    )
    result = case1_entry_zone(ticker="CASE1", assumptions=assumptions, current_eps=5, plausible_eps_growth=0.20, required_return=0.15, currency="USD", actual_shares=100)
    assert result.bands[2].entry_price == pytest.approx(5 * 1.2**3 * 20 / 1.15**3)
    assert result.bands[2].maximum_market_cap == pytest.approx(result.bands[2].entry_price * 100)
    assert result.valuation_assumption_version == 7


@pytest.mark.parametrize(
    ("metric", "stage", "margin"),
    ((ValuationMetric.EV_REVENUE, TerminalStage.GROWTH, 1.0), (ValuationMetric.EV_GROSS_PROFIT, TerminalStage.GROWTH, 0.50), (ValuationMetric.EV_EBIT, TerminalStage.TRANSITION, 0.20)),
)
def test_case2_reverse_formula_by_terminal_metric(metric, stage, margin):
    assumptions = case2_assumptions(metric, stage=stage)
    result = case2_entry_zone(ticker="CASE2", assumptions=assumptions, current_revenue=100, plausible_revenue_growth=0.30, required_return=0.15, currency="USD", actual_shares=10)
    future_revenue = 100 * 1.3**5
    expected_future_ev = future_revenue * margin * 5
    expected_market_cap = (expected_future_ev - 10) / (1.15**5 * 1.05**5)
    assert result.bands[1].maximum_market_cap == pytest.approx(expected_market_cap)
    assert result.bands[1].entry_price == pytest.approx(expected_market_cap / 10)
    assert result.valuation_assumption_version == 3


def test_higher_return_and_dilution_lower_case2_entry_price():
    base = case2_assumptions(dilution=0.02)
    high_dilution = case2_assumptions(dilution=0.20)
    low_return = case2_entry_zone(ticker="CASE2", assumptions=base, current_revenue=100, plausible_revenue_growth=0.30, required_return=0.10, currency="USD", actual_shares=10)
    high_return = case2_entry_zone(ticker="CASE2", assumptions=base, current_revenue=100, plausible_revenue_growth=0.30, required_return=0.20, currency="USD", actual_shares=10)
    diluted = case2_entry_zone(ticker="CASE2", assumptions=high_dilution, current_revenue=100, plausible_revenue_growth=0.30, required_return=0.10, currency="USD", actual_shares=10)
    assert high_return.bands[1].entry_price < low_return.bands[1].entry_price
    assert diluted.bands[1].entry_price < low_return.bands[1].entry_price
