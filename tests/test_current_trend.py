from pathlib import Path

import pytest
from pydantic import ValidationError

from engine.case1_snapshot import build_case1_snapshot
from engine.current_financials import RawCurrentTrendInput, load_current_trend_input
from engine.current_trend import (
    attach_current_trend,
    balance_sheet_signal,
    build_current_trend_overlay,
    cash_economics_signal,
    growth_signal,
    margin_signal,
    overall_current_signal,
)
from engine.financials import load_financial_history
from engine.models import CapitalModel, Grade


ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    ("current", "expected"),
    [(0.23, "positive"), (0.16, "neutral"), (0.07, "negative")],
)
def test_revenue_and_operating_growth_signal(current, expected):
    assert growth_signal(0.15, current) == expected


@pytest.mark.parametrize(
    ("current", "expected"),
    [(0.12, "positive"), (0.105, "neutral"), (0.085, "negative")],
)
def test_margin_signal(current, expected):
    assert margin_signal(0.10, current) == expected


@pytest.mark.parametrize(
    ("current", "expected"),
    [(1.20, "positive"), (0.95, "neutral"), (0.80, "negative")],
)
def test_cash_economics_signal(current, expected):
    assert cash_economics_signal(1.0, current) == expected


@pytest.mark.parametrize(
    ("current", "expected"),
    [(1.4, "positive"), (2.2, "neutral"), (2.7, "negative")],
)
def test_balance_sheet_signal(current, expected):
    assert balance_sheet_signal(2.0, current) == expected


def test_overall_current_signal_rules():
    assert overall_current_signal(
        ["positive", "positive", "positive", "neutral", "neutral"]
    ) == "positive"
    assert overall_current_signal(
        ["positive", "positive", "negative", "negative", "neutral"]
    ) == "mixed"
    assert overall_current_signal(
        ["positive", "unresolved", "unresolved", "unresolved", "neutral"]
    ) == "unresolved"


def test_current_input_rejects_lookahead_source():
    with pytest.raises(ValidationError, match="filing_date cannot be later"):
        RawCurrentTrendInput.model_validate(
            {
                "ticker": "TEST",
                "currency": "USD",
                "unit_scale": "units",
                "as_of": "2026-08-01",
                "period_label": "2026 Q2",
                "current": {
                    "period_end": "2026-06-30",
                    "period_type": "quarter",
                    "sources": [
                        {
                            "type": "filing",
                            "reference": "official",
                            "filing_date": "2026-08-02",
                            "retrieved_at": "2026-08-03T00:00:00Z"
                        }
                    ]
                },
                "prior_comparable": {
                    "period_end": "2025-06-30",
                    "period_type": "quarter",
                    "sources": [
                        {
                            "type": "filing",
                            "reference": "official",
                            "filing_date": "2025-08-01",
                            "retrieved_at": "2026-08-03T00:00:00Z"
                        }
                    ]
                }
            }
        )


def test_strl_current_overlay_reproduces_official_h1_data():
    annual = load_financial_history(ROOT / "data" / "raw" / "STRL.json")
    current = load_current_trend_input(
        ROOT / "data" / "current" / "STRL_2026_Q2.json"
    )
    annual_snapshot = build_case1_snapshot(annual, CapitalModel.PROJECT_BASED)
    overlay = build_current_trend_overlay(annual, current)
    combined = attach_current_trend(annual_snapshot, overlay)

    assert current.current.revenue == 1_993_854_000
    assert current.current_ttm_ebitda == 672_448_000
    assert annual_snapshot.quant_score == pytest.approx(3.65)
    assert annual_snapshot.quant_grade == Grade.A
    assert annual_snapshot.quant_based_on == "FY2022-FY2025"
    assert combined.quant_score == annual_snapshot.quant_score
    assert combined.quant_grade == annual_snapshot.quant_grade
    assert combined.current_trend == overlay
    assert overlay.revenue_growth.signal == "positive"
    assert overlay.operating_profit_growth.signal == "positive"
    assert overlay.margin_trend.signal == "positive"
    assert overlay.cash_economics.signal == "negative"
    assert overlay.balance_sheet.signal == "neutral"
    assert overlay.overall_signal == "neutral"


@pytest.mark.parametrize(
    ("fixture", "capital_model", "score", "grade"),
    [
        ("003230_KS.json", CapitalModel.MANUFACTURING, 4.00, Grade.A),
        ("LLY.json", CapitalModel.RD_IP_DRIVEN, 3.80, Grade.A),
        ("STRL.json", CapitalModel.PROJECT_BASED, 3.65, Grade.A),
        ("010120_KS.json", CapitalModel.MANUFACTURING, 3.15, Grade.B),
        ("ORCL.json", CapitalModel.CAPITAL_INTENSIVE, 2.70, Grade.C),
    ],
)
def test_annual_quant_regression_is_unchanged(fixture, capital_model, score, grade):
    history = load_financial_history(ROOT / "data" / "raw" / fixture)
    snapshot = build_case1_snapshot(history, capital_model)

    assert snapshot.quant_score == pytest.approx(score)
    assert snapshot.quant_grade == grade
