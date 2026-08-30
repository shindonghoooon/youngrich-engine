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


FIXTURE = Path(__file__).parents[1] / "data" / "raw" / "ORCL.json"


@pytest.fixture
def orcl_history():
    return load_financial_history(FIXTURE)


def test_orcl_fixture_parses_and_sorts_non_calendar_fiscal_years(orcl_history):
    assert [period.fiscal_year for period in orcl_history.periods] == [
        2023,
        2024,
        2025,
        2026,
    ]
    assert [period.fiscal_period_end.isoformat() for period in orcl_history.periods] == [
        "2023-05-31",
        "2024-05-31",
        "2025-05-31",
        "2026-05-31",
    ]
    assert orcl_history.periods[-1].revenue == 67_357_000_000


def test_orcl_three_year_growth_and_margin_metrics(orcl_history):
    assert revenue_cagr_3y(orcl_history) == pytest.approx(0.1047673282)
    assert operating_income_cagr_3y(orcl_history) == pytest.approx(0.1631922748)
    assert operating_margin_change_3y(orcl_history) == pytest.approx(4.3821042826)
    assert diluted_share_cagr_3y(orcl_history) == pytest.approx(0.0175266451)
    assert diluted_eps_cagr_3y(orcl_history) == pytest.approx(0.2383499561)


def test_orcl_cash_economics_preserves_reinvestment_tag_rule(orcl_history):
    conversion = cumulative_cfo_to_net_income_3y(orcl_history)
    capex_ratio = cumulative_capex_to_cfo_3y(orcl_history)
    snapshot = build_case1_snapshot(orcl_history, CapitalModel.CAPITAL_INTENSIVE)
    cash_economics = next(
        metric for metric in snapshot.metrics if metric.name == "cash_economics"
    )

    assert conversion == pytest.approx(71_471 / 39_997)
    assert capex_ratio == pytest.approx(83_744 / 71_471)
    assert reinvestment_intensity(83_744, 71_471) == "very_high"
    assert cash_economics.value == pytest.approx(conversion)
    assert cash_economics.grade == Grade.A
    assert cash_economics.supporting_tag == "very_high"


def test_orcl_standardized_roic_and_balance_sheet(orcl_history):
    beginning = orcl_history.periods[-2]
    ending = orcl_history.periods[-1]

    assert effective_tax_rate(ending) == pytest.approx(2_467 / 19_554)
    assert invested_capital(beginning) == 102_751_000_000
    assert invested_capital(ending) == 141_308_000_000
    assert roic_for_period(beginning, ending) == pytest.approx(0.1475567470)
    assert ending.supplied_ebitda == 29_900_000_000
    assert net_debt_to_ebitda(orcl_history) == pytest.approx(98_252 / 29_900)


def test_orcl_fixture_reproduces_complete_case1_snapshot(orcl_history):
    snapshot = build_case1_snapshot(orcl_history, CapitalModel.CAPITAL_INTENSIVE)

    assert snapshot.ticker == "ORCL"
    assert snapshot.as_of == "2026-05-31"
    assert snapshot.capital_model == CapitalModel.CAPITAL_INTENSIVE
    assert len(snapshot.metrics) == 8
    assert sum(metric.weight for metric in snapshot.metrics) == pytest.approx(1.0)
    assert all(metric.grade is not None for metric in snapshot.metrics)

    grades = {metric.name: metric.grade for metric in snapshot.metrics}
    assert grades == {
        "revenue_growth": Grade.C,
        "operating_profit_growth": Grade.C,
        "margin_trend": Grade.A,
        "cash_economics": Grade.A,
        "capital_efficiency": Grade.B,
        "balance_sheet": Grade.D,
        "dilution": Grade.B,
        "per_share_growth": Grade.B,
    }
    assert snapshot.quant_score == pytest.approx(2.7)
    assert snapshot.quant_grade == Grade.C


def test_strl_quant_snapshot_regression_remains_unchanged():
    fixture = Path(__file__).parents[1] / "data" / "raw" / "STRL.json"
    history = load_financial_history(fixture)
    snapshot = build_case1_snapshot(history, CapitalModel.PROJECT_BASED)

    assert snapshot.quant_score == pytest.approx(3.65)
    assert snapshot.quant_grade == Grade.A
