from __future__ import annotations

import json
from pathlib import Path

from engine.cases.profitable_growth import (
    grade_cash_conversion,
    grade_dilution,
    grade_margin_change,
    grade_net_debt_ebitda,
    grade_operating_profit_growth,
    grade_per_share_growth,
    grade_revenue_growth,
    grade_roic,
    reinvestment_intensity,
)
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
from engine.financials import FinancialHistory
from engine.models import AnalysisSnapshot, CapitalModel, CaseType, MetricResult, Trend
from engine.scoring import quant_grade, weighted_quant_score


_CONFIG_PATH = Path(__file__).parents[1] / "config" / "profitable_growth.json"
WEIGHTS = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))["weights"]


def _growth_trend(latest_yoy: float, cagr_3y: float) -> Trend:
    if cagr_3y <= 0:
        return Trend.NA
    if latest_yoy > cagr_3y * 1.2:
        return Trend.ACCELERATING
    if latest_yoy < cagr_3y * 0.8:
        return Trend.DECELERATING
    return Trend.STABLE


def build_case1_snapshot(
    history: FinancialHistory,
    capital_model: CapitalModel,
) -> AnalysisSnapshot:
    latest = history.periods[-1]
    previous = history.periods[-2]

    revenue_growth = revenue_cagr_3y(history)
    operating_growth = operating_income_cagr_3y(history)
    margin_change = operating_margin_change_3y(history)
    cash_conversion = cumulative_cfo_to_net_income_3y(history)
    capex_intensity = cumulative_capex_to_cfo_3y(history)
    balance_sheet = net_debt_to_ebitda(history)
    dilution = diluted_share_cagr_3y(history)
    eps_growth = diluted_eps_cagr_3y(history)

    metrics = [
        MetricResult(
            name="revenue_growth",
            value=revenue_growth,
            unit="ratio",
            grade=grade_revenue_growth(revenue_growth),
            trend=_growth_trend(latest.revenue / previous.revenue - 1, revenue_growth),
            weight=WEIGHTS["revenue_growth"],
        ),
        MetricResult(
            name="operating_profit_growth",
            value=operating_growth,
            unit="ratio",
            grade=grade_operating_profit_growth(operating_growth),
            trend=_growth_trend(
                latest.operating_income / previous.operating_income - 1,
                operating_growth,
            ),
            weight=WEIGHTS["operating_profit_growth"],
        ),
        MetricResult(
            name="margin_trend",
            value=margin_change,
            unit="pct_point",
            grade=grade_margin_change(margin_change),
            weight=WEIGHTS["margin_trend"],
        ),
        MetricResult(
            name="cash_economics",
            value=cash_conversion,
            unit="cfo_to_net_income",
            grade=grade_cash_conversion(
                sum(period.cfo for period in history.periods[-3:]),
                sum(period.net_income for period in history.periods[-3:]),
            ),
            weight=WEIGHTS["cash_economics"],
            supporting_tag=reinvestment_intensity(
                sum(period.capex for period in history.periods[-3:]),
                sum(period.cfo for period in history.periods[-3:]),
            ),
            note=f"3Y CAPEX/CFO={capex_intensity:.4f}; tag does not alter grade",
        ),
        MetricResult(
            name="capital_efficiency",
            value=latest.supplied_roic,
            unit="ratio",
            grade=grade_roic(latest.supplied_roic) if latest.supplied_roic is not None else None,
            weight=WEIGHTS["capital_efficiency"],
            supporting_tag="supplied_roic_required",
            note="TODO: no engine ROIC formula is fixed in v1",
        ),
        MetricResult(
            name="balance_sheet",
            value=balance_sheet,
            unit="net_debt_ebitda",
            grade=grade_net_debt_ebitda(balance_sheet),
            weight=WEIGHTS["balance_sheet"],
        ),
        MetricResult(
            name="dilution",
            value=dilution,
            unit="ratio",
            grade=grade_dilution(dilution),
            weight=WEIGHTS["dilution"],
        ),
        MetricResult(
            name="per_share_growth",
            value=eps_growth,
            unit="ratio",
            grade=grade_per_share_growth(eps_growth),
            weight=WEIGHTS["per_share_growth"],
        ),
    ]

    score = None
    grade = None
    if all(metric.grade is not None for metric in metrics):
        score = weighted_quant_score(metrics)
        grade = quant_grade(score)

    return AnalysisSnapshot(
        ticker=history.ticker,
        company_name=history.company_name,
        as_of=latest.fiscal_period_end.isoformat(),
        case=CaseType.PROFITABLE_GROWTH,
        capital_model=capital_model,
        quant_score=score,
        quant_grade=grade,
        metrics=metrics,
    )
