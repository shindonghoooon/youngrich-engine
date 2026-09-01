from pathlib import Path

import pytest

from engine.case1_snapshot import build_case1_snapshot
from engine.cases.profitable_growth import reinvestment_intensity
from engine.financial_metrics import (
    cumulative_capex_to_cfo_3y,
    cumulative_cfo_to_net_income_3y,
    diluted_eps_cagr_3y,
    diluted_share_cagr_3y,
    effective_tax_rate,
    invested_capital,
    net_debt_to_ebitda,
    operating_income_cagr_3y,
    operating_margin_change_3y,
    revenue_cagr_3y,
    roic_for_period,
)
from engine.financials import load_financial_history
from engine.models import CapitalModel, Grade


RAW_DATA = Path(__file__).parents[1] / "data" / "raw"

CASES = {
    "003230_KS.json": {
        "ticker": "003230.KS",
        "capital_model": CapitalModel.MANUFACTURING,
        "revenue_cagr": 0.3727941828,
        "operating_cagr": 0.7967126155,
        "margin_change": 12.3470393267,
        "cfo_conversion": 1.0620086023,
        "capex_to_cfo": 0.8648895177,
        "capex_tag": "high",
        "roic": 0.3609780330,
        "net_debt_ebitda": 0.1810204380,
        "dilution_cagr": -0.0006917578,
        "eps_cagr": 0.6973880447,
        "grades": ["A", "A", "A", "A", "A", "A", "A", "A"],
        "score": 4.0,
        "quant_grade": Grade.A,
    },
    "LLY.json": {
        "ticker": "LLY",
        "capital_model": CapitalModel.RD_IP_DRIVEN,
        "revenue_cagr": 0.3168737488,
        "operating_cagr": 0.5453300317,
        "margin_change": 15.3816927297,
        "cfo_conversion": 0.8190477757,
        "capex_to_cfo": 0.5472331023,
        "capex_tag": "moderate",
        "roic": 0.3965145728,
        "net_debt_ebitda": 1.2450969999,
        "dilution_cagr": -0.0019637951,
        "eps_cagr": 0.4927183319,
        "grades": ["A", "A", "A", "B", "A", "B", "A", "A"],
        "score": 3.8,
        "quant_grade": Grade.A,
    },
    "010120_KS.json": {
        "ticker": "010120.KS",
        "capital_model": CapitalModel.MANUFACTURING,
        "revenue_cagr": 0.1371462819,
        "operating_cagr": 0.3149902254,
        "margin_change": 3.0340185453,
        "cfo_conversion": 1.0144030074,
        "capex_to_cfo": 0.6163019172,
        "capex_tag": "high",
        "roic": 0.1153490607,
        "net_debt_ebitda": 1.0374998800,
        "dilution_cagr": 0.0041160595,
        "eps_cagr": 0.4635972813,
        "grades": ["C", "A", "A", "A", "C", "B", "B", "A"],
        "score": 3.15,
        "quant_grade": Grade.B,
    },
}


@pytest.mark.parametrize(("fixture_name", "expected"), CASES.items())
def test_additional_fixture_validation_and_fiscal_period_sorting(
    fixture_name, expected
):
    history = load_financial_history(RAW_DATA / fixture_name)

    assert history.ticker == expected["ticker"]
    assert [period.fiscal_year for period in history.periods] == [
        2022,
        2023,
        2024,
        2025,
    ]
    assert [period.fiscal_period_end.isoformat() for period in history.periods] == [
        "2022-12-31",
        "2023-12-31",
        "2024-12-31",
        "2025-12-31",
    ]
    assert all(period.sources for period in history.periods)


@pytest.mark.parametrize(("fixture_name", "expected"), CASES.items())
def test_additional_fixture_reproduces_all_case1_metrics(fixture_name, expected):
    history = load_financial_history(RAW_DATA / fixture_name)
    latest = history.periods[-1]
    previous = history.periods[-2]

    assert revenue_cagr_3y(history) == pytest.approx(expected["revenue_cagr"])
    assert operating_income_cagr_3y(history) == pytest.approx(
        expected["operating_cagr"]
    )
    assert operating_margin_change_3y(history) == pytest.approx(
        expected["margin_change"]
    )
    assert cumulative_cfo_to_net_income_3y(history) == pytest.approx(
        expected["cfo_conversion"]
    )
    assert cumulative_capex_to_cfo_3y(history) == pytest.approx(
        expected["capex_to_cfo"]
    )
    assert reinvestment_intensity(
        sum(period.capex for period in history.periods[-3:]),
        sum(period.cfo for period in history.periods[-3:]),
    ) == expected["capex_tag"]
    assert roic_for_period(previous, latest) == pytest.approx(expected["roic"])
    assert net_debt_to_ebitda(history) == pytest.approx(
        expected["net_debt_ebitda"]
    )
    assert diluted_share_cagr_3y(history) == pytest.approx(
        expected["dilution_cagr"]
    )
    assert diluted_eps_cagr_3y(history) == pytest.approx(expected["eps_cagr"])


@pytest.mark.parametrize(("fixture_name", "expected"), CASES.items())
def test_additional_fixture_reproduces_complete_case1_snapshot(
    fixture_name, expected
):
    history = load_financial_history(RAW_DATA / fixture_name)
    snapshot = build_case1_snapshot(history, expected["capital_model"])

    assert snapshot.ticker == expected["ticker"]
    assert snapshot.as_of == "2025-12-31"
    assert snapshot.capital_model == expected["capital_model"]
    assert len(snapshot.metrics) == 8
    assert sum(metric.weight for metric in snapshot.metrics) == pytest.approx(1.0)
    assert [metric.grade.value for metric in snapshot.metrics] == expected["grades"]
    assert snapshot.quant_score == pytest.approx(expected["score"])
    assert snapshot.quant_grade == expected["quant_grade"]


@pytest.mark.parametrize("fixture_name", CASES)
def test_roic_inputs_are_reproducible_from_normalized_periods(fixture_name):
    history = load_financial_history(RAW_DATA / fixture_name)
    previous = history.periods[-2]
    latest = history.periods[-1]

    assert effective_tax_rate(latest) is not None
    assert invested_capital(previous) > 0
    assert invested_capital(latest) > 0
    assert roic_for_period(previous, latest) is not None


def test_existing_strl_and_orcl_quant_regressions_remain_unchanged():
    strl = build_case1_snapshot(
        load_financial_history(RAW_DATA / "STRL.json"), CapitalModel.PROJECT_BASED
    )
    orcl = build_case1_snapshot(
        load_financial_history(RAW_DATA / "ORCL.json"),
        CapitalModel.CAPITAL_INTENSIVE,
    )

    assert strl.quant_score == pytest.approx(3.65)
    assert strl.quant_grade == Grade.A
    assert orcl.quant_score == pytest.approx(2.70)
    assert orcl.quant_grade == Grade.C
