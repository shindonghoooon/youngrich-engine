from datetime import date
from pathlib import Path

import pytest

from engine.case1_snapshot import build_case1_snapshot
from engine.current_financials import load_current_trend_input
from engine.current_trend import build_current_trend_overlay
from engine.financials import load_financial_history
from engine.models import CapitalModel, Grade


ROOT = Path(__file__).parents[1]
RAW_DATA = ROOT / "data" / "raw"
CURRENT_DATA = ROOT / "data" / "current"

CURRENT_CASES = {
    "003230.KS": {
        "annual_fixture": "003230_KS.json",
        "current_fixture": "003230_KS_2026_Q2.json",
        "capital_model": CapitalModel.MANUFACTURING,
        "score": 4.00,
        "grade": Grade.A,
        "signals": ("neutral", "negative", "neutral", "negative", "neutral"),
        "overall": "neutral",
    },
    "LLY": {
        "annual_fixture": "LLY.json",
        "current_fixture": "LLY_2026_Q2.json",
        "capital_model": CapitalModel.RD_IP_DRIVEN,
        "score": 3.80,
        "grade": Grade.A,
        "signals": ("positive", "positive", "positive", "positive", "neutral"),
        "overall": "positive",
    },
    "010120.KS": {
        "annual_fixture": "010120_KS.json",
        "current_fixture": "010120_KS_2026_Q2.json",
        "capital_model": CapitalModel.MANUFACTURING,
        "score": 3.15,
        "grade": Grade.B,
        "signals": ("positive", "positive", "positive", "negative", "neutral"),
        "overall": "positive",
    },
}


@pytest.mark.parametrize(("ticker", "expected"), CURRENT_CASES.items())
def test_official_current_fixture_is_comparable_and_has_no_lookahead(
    ticker, expected
):
    current = load_current_trend_input(CURRENT_DATA / expected["current_fixture"])

    assert current.ticker == ticker
    assert current.as_of == date(2026, 9, 1)
    assert current.current.period_type == "ytd"
    assert current.prior_comparable.period_type == "ytd"
    assert current.current.period_end == date(2026, 6, 30)
    assert current.prior_comparable.period_end == date(2025, 6, 30)
    assert all(
        source.filing_date <= current.as_of
        for period in (current.current, current.prior_comparable)
        for source in period.sources
    )


@pytest.mark.parametrize(("ticker", "expected"), CURRENT_CASES.items())
def test_cross_company_current_overlay_and_annual_quant_regression(ticker, expected):
    annual = load_financial_history(RAW_DATA / expected["annual_fixture"])
    current = load_current_trend_input(CURRENT_DATA / expected["current_fixture"])
    snapshot = build_case1_snapshot(annual, expected["capital_model"])
    overlay = build_current_trend_overlay(annual, current)

    assert snapshot.quant_score == pytest.approx(expected["score"])
    assert snapshot.quant_grade == expected["grade"]
    assert (
        overlay.revenue_growth.signal,
        overlay.operating_profit_growth.signal,
        overlay.margin_trend.signal,
        overlay.cash_economics.signal,
        overlay.balance_sheet.signal,
    ) == expected["signals"]
    assert overlay.overall_signal == expected["overall"]


def test_lilly_uses_reproducible_reported_gaap_operating_income():
    current = load_current_trend_input(CURRENT_DATA / "LLY_2026_Q2.json")

    current_gaap_operating_income = 42_773 - (
        6_845 + 7_329 + 6_364 + 3_360 + 982
    )
    prior_gaap_operating_income = 28_286 - (
        4_672 + 6_070 + 5_221 + 1_726 + 35
    )

    assert current.current.operating_income == current_gaap_operating_income * 1e6
    assert (
        current.prior_comparable.operating_income
        == prior_gaap_operating_income * 1e6
    )


@pytest.mark.parametrize(
    ("fixture", "expected_ttm_ebitda"),
    [
        ("003230_KS_2026_Q2.json", 700_311_593_066),
        ("LLY_2026_Q2.json", 35_732_000_000),
        ("010120_KS_2026_Q2.json", 676_334_298_191),
    ],
)
def test_ttm_ebitda_uses_official_period_bridge(fixture, expected_ttm_ebitda):
    current = load_current_trend_input(CURRENT_DATA / fixture)

    assert current.current_ttm_ebitda == expected_ttm_ebitda


def test_ttm_ebitda_bridge_components_are_reproducible():
    samyang = 587_937_783_060 + (353_313_697_185 + 40_783_045_000) - (
        254_076_409_179 + 27_646_523_000
    )
    lilly = 28_299 + (17_893 + 1_043) - (10_562 + 941)
    ls_electric = 558_723_357_101 + (
        305_087_151_603 + 72_017_298_934
    ) - (195_907_352_623 + 63_586_156_824)

    assert samyang == 700_311_593_066
    assert lilly == 35_732
    assert ls_electric == 676_334_298_191


def test_orcl_is_legitimately_unresolved_without_post_fy2026_period():
    annual = load_financial_history(RAW_DATA / "ORCL.json")
    snapshot = build_case1_snapshot(annual, CapitalModel.CAPITAL_INTENSIVE)

    assert annual.periods[-1].fiscal_period_end == date(2026, 5, 31)
    assert snapshot.quant_score == pytest.approx(2.70)
    assert snapshot.quant_grade == Grade.C
    assert not (CURRENT_DATA / "ORCL_2026_latest.json").exists()
