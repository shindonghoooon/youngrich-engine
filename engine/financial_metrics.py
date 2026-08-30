from __future__ import annotations

from engine.financials import FinancialHistory, FinancialPeriod


def cagr(start_value: float, end_value: float, years: int) -> float:
    if start_value <= 0 or end_value < 0:
        raise ValueError("CAGR requires a positive start and non-negative end value")
    if years <= 0:
        raise ValueError("CAGR years must be positive")
    return (end_value / start_value) ** (1 / years) - 1


def trailing_periods(history: FinancialHistory, count: int) -> list[FinancialPeriod]:
    if len(history.periods) < count:
        raise ValueError(f"at least {count} annual periods are required")
    return history.periods[-count:]


def revenue_cagr_3y(history: FinancialHistory) -> float:
    periods = trailing_periods(history, 4)
    return cagr(periods[0].revenue, periods[-1].revenue, len(periods) - 1)


def operating_income_cagr_3y(history: FinancialHistory) -> float:
    periods = trailing_periods(history, 4)
    return cagr(periods[0].operating_income, periods[-1].operating_income, len(periods) - 1)


def operating_margin_change_3y(history: FinancialHistory) -> float:
    periods = trailing_periods(history, 4)
    start_margin = periods[0].operating_income / periods[0].revenue
    end_margin = periods[-1].operating_income / periods[-1].revenue
    return (end_margin - start_margin) * 100


def cumulative_cfo_to_net_income_3y(history: FinancialHistory) -> float:
    periods = trailing_periods(history, 3)
    net_income = sum(period.net_income for period in periods)
    if net_income <= 0:
        raise ValueError("cumulative net income must be positive")
    return sum(period.cfo for period in periods) / net_income


def cumulative_capex_to_cfo_3y(history: FinancialHistory) -> float:
    periods = trailing_periods(history, 3)
    cfo = sum(period.cfo for period in periods)
    if cfo <= 0:
        raise ValueError("cumulative CFO must be positive")
    return sum(period.capex for period in periods) / cfo


def net_debt_to_ebitda(history: FinancialHistory) -> float:
    latest = trailing_periods(history, 1)[0]
    if latest.supplied_ebitda is None or latest.supplied_ebitda <= 0:
        raise ValueError("latest period requires a positive supplied_ebitda")
    return (latest.total_debt - latest.cash) / latest.supplied_ebitda


def diluted_share_cagr_3y(history: FinancialHistory) -> float:
    periods = trailing_periods(history, 4)
    return cagr(periods[0].diluted_shares, periods[-1].diluted_shares, len(periods) - 1)


def diluted_eps_cagr_3y(history: FinancialHistory) -> float:
    periods = trailing_periods(history, 4)
    return cagr(periods[0].diluted_eps, periods[-1].diluted_eps, len(periods) - 1)
