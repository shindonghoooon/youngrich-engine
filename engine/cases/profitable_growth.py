from __future__ import annotations

from engine.models import Grade


def grade_revenue_growth(cagr: float) -> Grade:
    if cagr >= 0.25:
        return Grade.A
    if cagr >= 0.15:
        return Grade.B
    if cagr >= 0.08:
        return Grade.C
    if cagr >= 0:
        return Grade.D
    return Grade.X


def grade_operating_profit_growth(cagr: float) -> Grade:
    if cagr >= 0.30:
        return Grade.A
    if cagr >= 0.18:
        return Grade.B
    if cagr >= 0.08:
        return Grade.C
    if cagr >= 0:
        return Grade.D
    return Grade.X


def grade_margin_change(change_pct_point: float) -> Grade:
    if change_pct_point >= 3:
        return Grade.A
    if change_pct_point >= 1:
        return Grade.B
    if change_pct_point >= -1:
        return Grade.C
    if change_pct_point >= -3:
        return Grade.D
    return Grade.X


def grade_roic(roic: float) -> Grade:
    if roic >= 0.20:
        return Grade.A
    if roic >= 0.12:
        return Grade.B
    if roic >= 0.08:
        return Grade.C
    if roic >= 0.05:
        return Grade.D
    return Grade.X


def grade_net_debt_ebitda(value: float) -> Grade:
    # Negative means net cash.
    if value <= 1:
        return Grade.A
    if value <= 2:
        return Grade.B
    if value <= 3:
        return Grade.C
    if value <= 4:
        return Grade.D
    return Grade.X


def grade_dilution(cagr: float) -> Grade:
    if cagr <= 0:
        return Grade.A
    if cagr <= 0.02:
        return Grade.B
    if cagr <= 0.05:
        return Grade.C
    if cagr <= 0.10:
        return Grade.D
    return Grade.X


def grade_per_share_growth(cagr: float) -> Grade:
    if cagr >= 0.25:
        return Grade.A
    if cagr >= 0.15:
        return Grade.B
    if cagr >= 0.08:
        return Grade.C
    if cagr >= 0:
        return Grade.D
    return Grade.X
