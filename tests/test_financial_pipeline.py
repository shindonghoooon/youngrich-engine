from pathlib import Path

import pytest

from engine.case1_snapshot import WEIGHTS, build_case1_snapshot
from engine.cases.profitable_growth import reinvestment_intensity
from engine.financial_metrics import (
    cumulative_capex_to_cfo_3y,
    cumulative_cfo_to_net_income_3y,
    diluted_eps_cagr_3y,
    diluted_share_cagr_3y,
    net_debt_to_ebitda,
    operating_income_cagr_3y,
    operating_margin_change_3y,
    revenue_cagr_3y,
)
from engine.financials import load_financial_history
from engine.models import CapitalModel, Grade


FIXTURE = Path(__file__).parents[1] / "data" / "raw" / "STRL.json"


@pytest.fixture
def strl_history():
    return load_financial_history(FIXTURE)


def test_normalization_sorts_years_and_scales_currency(strl_history):
    assert [period.fiscal_year for period in strl_history.periods] == [2022, 2023, 2024, 2025]
    assert [period.fiscal_period_end.isoformat() for period in strl_history.periods] == [
        "2022-12-31",
        "2023-12-31",
        "2024-12-31",
        "2025-12-31",
    ]
    assert strl_history.currency == "USD"
    assert strl_history.periods[-1].revenue == 2_490_049_000


def test_three_year_cagrs(strl_history):
    assert revenue_cagr_3y(strl_history) == pytest.approx(0.1206182169)
    assert operating_income_cagr_3y(strl_history) == pytest.approx(0.3642367102)
    assert diluted_share_cagr_3y(strl_history) == pytest.approx(0.0041597003)
    assert diluted_eps_cagr_3y(strl_history) == pytest.approx(0.4371604328)


def test_margin_and_cash_economics(strl_history):
    assert operating_margin_change_3y(strl_history) == pytest.approx(7.2664442312)
    assert cumulative_cfo_to_net_income_3y(strl_history) == pytest.approx(2.0628587332)
    capex_ratio = cumulative_capex_to_cfo_3y(strl_history)
    assert capex_ratio == pytest.approx(0.1572711553)
    assert reinvestment_intensity(
        sum(period.capex for period in strl_history.periods[-3:]),
        sum(period.cfo for period in strl_history.periods[-3:]),
    ) == "low"


def test_latest_net_debt_to_ebitda(strl_history):
    assert net_debt_to_ebitda(strl_history) == pytest.approx(-0.2072860169)


def test_case1_weights_sum_to_one():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_strl_fixture_reproduces_quant_snapshot(strl_history):
    snapshot = build_case1_snapshot(strl_history, CapitalModel.PROJECT_BASED)

    assert snapshot.ticker == "STRL"
    assert snapshot.as_of == "2025-12-31"
    assert len(snapshot.metrics) == 8
    assert [metric.name for metric in snapshot.metrics] == list(WEIGHTS)
    assert sum(metric.weight for metric in snapshot.metrics) == pytest.approx(1.0)

    grades = {metric.name: metric.grade for metric in snapshot.metrics}
    assert grades == {
        "revenue_growth": Grade.C,
        "operating_profit_growth": Grade.A,
        "margin_trend": Grade.A,
        "cash_economics": Grade.A,
        "capital_efficiency": None,
        "balance_sheet": Grade.A,
        "dilution": Grade.B,
        "per_share_growth": Grade.A,
    }
    assert snapshot.quant_score is None
    assert snapshot.quant_grade is None
