from __future__ import annotations

from engine.current_financials import CurrentTrendInput
from engine.financial_metrics import (
    cumulative_cfo_to_net_income_3y,
    net_debt_to_ebitda,
    operating_income_cagr_3y,
    revenue_cagr_3y,
)
from engine.financials import FinancialHistory
from engine.models import (
    AnalysisSnapshot,
    CurrentMetricSignal,
    CurrentTrendOverlay,
    OverallCurrentSignal,
)


def growth_signal(base_growth: float, current_growth: float | None) -> str:
    if current_growth is None:
        return "unresolved"
    if current_growth > base_growth + 0.05:
        return "positive"
    if current_growth < base_growth - 0.05:
        return "negative"
    return "neutral"


def margin_signal(prior_margin: float | None, current_margin: float | None) -> str:
    if prior_margin is None or current_margin is None:
        return "unresolved"
    change_pp = (current_margin - prior_margin) * 100
    if change_pp >= 1.0:
        return "positive"
    if change_pp <= -1.0:
        return "negative"
    return "neutral"


def cash_economics_signal(
    base_conversion: float, current_conversion: float | None
) -> str:
    if current_conversion is None:
        return "unresolved"
    if current_conversion >= base_conversion * 1.10:
        return "positive"
    if current_conversion < base_conversion * 0.90:
        return "negative"
    return "neutral"


def balance_sheet_signal(base_ratio: float, current_ratio: float | None) -> str:
    if current_ratio is None:
        return "unresolved"
    change = current_ratio - base_ratio
    if change <= -0.5:
        return "positive"
    if change >= 0.5:
        return "negative"
    return "neutral"


def overall_current_signal(signals: list[str]) -> OverallCurrentSignal:
    resolved = [signal for signal in signals if signal != "unresolved"]
    if len(resolved) < 3:
        return "unresolved"
    positive = resolved.count("positive")
    negative = resolved.count("negative")
    if positive >= 3 and negative == 0:
        return "positive"
    if negative >= 3 and positive == 0:
        return "negative"
    if positive >= 2 and negative >= 2:
        return "mixed"
    return "neutral"


def _safe_growth(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior <= 0:
        return None
    return current / prior - 1


def _safe_margin(operating_income: float | None, revenue: float | None) -> float | None:
    if operating_income is None or revenue is None or revenue <= 0:
        return None
    return operating_income / revenue


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def build_current_trend_overlay(
    annual_history: FinancialHistory,
    current_input: CurrentTrendInput,
) -> CurrentTrendOverlay:
    if annual_history.ticker != current_input.ticker:
        raise ValueError("annual history and current input ticker must match")

    current = current_input.current
    prior = current_input.prior_comparable
    current_revenue_growth = _safe_growth(current.revenue, prior.revenue)
    current_operating_growth = _safe_growth(
        current.operating_income, prior.operating_income
    )
    current_margin = _safe_margin(current.operating_income, current.revenue)
    prior_margin = _safe_margin(prior.operating_income, prior.revenue)
    current_conversion = _safe_ratio(current.cfo, current.net_income_consolidated)
    current_capex_to_cfo = _safe_ratio(current.capex, current.cfo)

    latest_annual = annual_history.periods[-1]
    base_balance = net_debt_to_ebitda(annual_history)
    current_balance = None
    if (
        current.cash is not None
        and current.total_debt is not None
        and current_input.current_ttm_ebitda is not None
    ):
        current_balance = (
            current.total_debt - current.cash
        ) / current_input.current_ttm_ebitda

    revenue = CurrentMetricSignal(
        metric="revenue_growth",
        signal=growth_signal(revenue_cagr_3y(annual_history), current_revenue_growth),
        observation=(
            f"current_yoy={current_revenue_growth:.4f}; "
            f"annual_3y_cagr={revenue_cagr_3y(annual_history):.4f}"
            if current_revenue_growth is not None
            else "comparable revenue unavailable"
        ),
    )
    operating = CurrentMetricSignal(
        metric="operating_profit_growth",
        signal=growth_signal(
            operating_income_cagr_3y(annual_history), current_operating_growth
        ),
        observation=(
            f"current_yoy={current_operating_growth:.4f}; "
            f"annual_3y_cagr={operating_income_cagr_3y(annual_history):.4f}"
            if current_operating_growth is not None
            else "comparable operating income unavailable"
        ),
    )
    margin = CurrentMetricSignal(
        metric="margin_trend",
        signal=margin_signal(prior_margin, current_margin),
        observation=(
            f"current_margin={current_margin:.4f}; prior_margin={prior_margin:.4f}; "
            f"change_pp={(current_margin - prior_margin) * 100:.4f}"
            if current_margin is not None and prior_margin is not None
            else "comparable operating margin unavailable"
        ),
    )
    cash = CurrentMetricSignal(
        metric="cash_economics",
        signal=cash_economics_signal(
            cumulative_cfo_to_net_income_3y(annual_history), current_conversion
        ),
        observation=(
            f"current_conversion={current_conversion:.4f}; "
            f"annual_conversion={cumulative_cfo_to_net_income_3y(annual_history):.4f}; "
            f"current_capex_to_cfo={current_capex_to_cfo:.4f}"
            if current_conversion is not None and current_capex_to_cfo is not None
            else "current cumulative CFO, net income, or CAPEX unavailable"
        ),
    )
    balance = CurrentMetricSignal(
        metric="balance_sheet",
        signal=balance_sheet_signal(base_balance, current_balance),
        observation=(
            f"current_net_debt_ebitda={current_balance:.4f}; "
            f"annual_net_debt_ebitda={base_balance:.4f}; "
            f"annual_period_end={latest_annual.fiscal_period_end.isoformat()}"
            if current_balance is not None
            else "current TTM EBITDA or quarter-end balance sheet unavailable"
        ),
    )
    signals = [
        revenue.signal,
        operating.signal,
        margin.signal,
        cash.signal,
        balance.signal,
    ]
    return CurrentTrendOverlay(
        as_of=current_input.as_of,
        period_label=current_input.period_label,
        revenue_growth=revenue,
        operating_profit_growth=operating,
        margin_trend=margin,
        cash_economics=cash,
        balance_sheet=balance,
        overall_signal=overall_current_signal(signals),
    )


def attach_current_trend(
    snapshot: AnalysisSnapshot, overlay: CurrentTrendOverlay
) -> AnalysisSnapshot:
    return snapshot.model_copy(update={"current_trend": overlay})
