"""Reverse frozen valuation equations into valuation-based entry ranges."""

from __future__ import annotations

from engine.tracking_models import (
    AnalysisCase,
    EntryZoneBand,
    EntryZoneResult,
    ExpectationGap,
    TerminalStage,
    ValuationAssumptionSet,
    ValuationMetric,
)


def case1_entry_zone(
    *,
    ticker: str,
    assumptions: ValuationAssumptionSet,
    current_eps: float,
    plausible_eps_growth: float,
    required_return: float,
    currency: str,
    actual_shares: float | None = None,
) -> EntryZoneResult:
    if assumptions.case != AnalysisCase.CASE_1_PROFITABLE_GROWTH:
        raise ValueError("Case 1 entry zone requires Case 1 assumptions")
    if assumptions.primary_metric != ValuationMetric.PE:
        raise ValueError("Case 1 v1 entry zone supports PE only")
    if current_eps <= 0 or actual_shares is not None and actual_shares <= 0:
        raise ValueError("EPS and supplied actual shares must be positive")
    if required_return not in assumptions.required_return_sensitivities:
        raise ValueError("required_return must be a configured sensitivity")
    future_eps = current_eps * (1 + plausible_eps_growth) ** assumptions.horizon_years
    discount = (1 + required_return) ** assumptions.horizon_years
    bands = tuple(
        EntryZoneBand(
            band=item.band,
            exit_multiple=item.value,
            entry_price=future_eps * item.value / discount,
            maximum_market_cap=(
                future_eps * item.value / discount * actual_shares
                if actual_shares is not None
                else None
            ),
        )
        for item in assumptions.exit_multiples
    )
    return EntryZoneResult(
        ticker=ticker,
        valuation_assumption_set_id=assumptions.assumption_set_id,
        valuation_assumption_version=assumptions.version,
        target_state=ExpectationGap.OVERLAP,
        bands=bands,
        currency=currency,
        required_return=required_return,
        horizon_years=assumptions.horizon_years,
        plausible_growth_used=plausible_eps_growth,
        rationale="Valuation entry boundary, not a technical support level",
    )


def case2_entry_zone(
    *,
    ticker: str,
    assumptions: ValuationAssumptionSet,
    current_revenue: float,
    plausible_revenue_growth: float,
    required_return: float,
    currency: str,
    actual_shares: float | None = None,
) -> EntryZoneResult:
    if assumptions.case != AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH:
        raise ValueError("Case 2 entry zone requires Case 2 assumptions")
    if current_revenue <= 0 or actual_shares is not None and actual_shares <= 0:
        raise ValueError("revenue and supplied actual shares must be positive")
    if required_return not in assumptions.required_return_sensitivities:
        raise ValueError("required_return must be a configured sensitivity")
    horizon = assumptions.horizon_years
    future_revenue = current_revenue * (1 + plausible_revenue_growth) ** horizon
    compound = (1 + required_return) ** horizon * (
        1 + assumptions.expected_annual_dilution
    ) ** horizon
    bands = []
    for item in assumptions.exit_multiples:
        if assumptions.terminal_stage == TerminalStage.GROWTH:
            if assumptions.primary_metric == ValuationMetric.EV_REVENUE:
                future_ev = future_revenue * item.value
            elif assumptions.primary_metric == ValuationMetric.EV_GROSS_PROFIT:
                if assumptions.target_gross_margin is None or assumptions.target_gross_margin <= 0:
                    raise ValueError("EV/GP requires a positive target_gross_margin")
                future_ev = future_revenue * assumptions.target_gross_margin * item.value
            else:
                raise ValueError("GROWTH entry zone requires EV/Revenue or EV/GP")
        else:
            if assumptions.primary_metric != ValuationMetric.EV_EBIT:
                raise ValueError("TRANSITION/MATURE entry zone requires EV/EBIT")
            if assumptions.target_operating_margin is None or assumptions.target_operating_margin <= 0:
                raise ValueError("EV/EBIT requires a positive target_operating_margin")
            future_ev = future_revenue * assumptions.target_operating_margin * item.value
        future_equity = future_ev - assumptions.terminal_net_debt
        if future_equity <= 0:
            raise ValueError("terminal equity value must be positive")
        market_cap = future_equity / compound
        bands.append(
            EntryZoneBand(
                band=item.band,
                exit_multiple=item.value,
                maximum_market_cap=market_cap,
                entry_price=market_cap / actual_shares if actual_shares is not None else None,
            )
        )
    return EntryZoneResult(
        ticker=ticker,
        valuation_assumption_set_id=assumptions.assumption_set_id,
        valuation_assumption_version=assumptions.version,
        target_state=ExpectationGap.OVERLAP,
        bands=tuple(bands),
        currency=currency,
        required_return=required_return,
        horizon_years=horizon,
        plausible_growth_used=plausible_revenue_growth,
        rationale="Valuation entry boundary, not a technical support level",
    )
