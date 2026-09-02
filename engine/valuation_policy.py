"""Pure formula contracts for Common Valuation v1.

Market prices and versioned assumptions are inputs. This module never fetches a price
or changes an assumption in response to a price move.
"""

from __future__ import annotations

from engine.tracking_models import (
    AssumptionRange,
    ExpectationGap,
    TerminalStage,
    ValuationConfidence,
    ValuationMetric,
)


CASE1_DEFAULT_HORIZON_YEARS = 3
CASE2_DEFAULT_HORIZON_YEARS = 5
REQUIRED_RETURN_SENSITIVITIES = (0.10, 0.15, 0.20)
DEFAULT_REQUIRED_RETURN = 0.15


def expectation_gap_for_ranges(
    *,
    required: AssumptionRange,
    plausible: AssumptionRange,
) -> ExpectationGap:
    if plausible.low > required.high:
        return ExpectationGap.POSITIVE
    if plausible.high < required.low:
        return ExpectationGap.NEGATIVE
    return ExpectationGap.OVERLAP


def derive_valuation_confidence(
    *,
    credible_evidence_count: int,
    company_economics_stable: bool,
    company_economics_rapidly_changing: bool,
    terminal_stage_confidence: ValuationConfidence,
) -> ValuationConfidence:
    if credible_evidence_count < 0:
        raise ValueError("credible_evidence_count cannot be negative")
    if company_economics_stable and company_economics_rapidly_changing:
        raise ValueError("company economics cannot be both stable and rapidly changing")
    if credible_evidence_count == 0:
        return ValuationConfidence.UNRESOLVED
    if (
        credible_evidence_count == 1
        or company_economics_rapidly_changing
        or terminal_stage_confidence == ValuationConfidence.LOW
    ):
        return ValuationConfidence.LOW
    if (
        credible_evidence_count >= 2
        and company_economics_stable
        and terminal_stage_confidence == ValuationConfidence.HIGH
    ):
        return ValuationConfidence.HIGH
    return ValuationConfidence.MEDIUM


def _require_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def case1_required_eps_cagr(
    *,
    current_price: float,
    current_eps: float,
    exit_pe: float,
    required_return: float = DEFAULT_REQUIRED_RETURN,
    horizon_years: int = CASE1_DEFAULT_HORIZON_YEARS,
) -> float:
    _require_positive("current_price", current_price)
    _require_positive("current_eps", current_eps)
    _require_positive("exit_pe", exit_pe)
    _require_positive("horizon_years", horizon_years)
    if required_return <= -1:
        raise ValueError("required_return must be greater than -100%")
    required_terminal_price = current_price * (1 + required_return) ** horizon_years
    required_terminal_eps = required_terminal_price / exit_pe
    return (required_terminal_eps / current_eps) ** (1 / horizon_years) - 1


def case2_required_future_equity_value(
    *,
    current_market_cap: float,
    required_return: float = DEFAULT_REQUIRED_RETURN,
    expected_annual_dilution: float,
    horizon_years: int = CASE2_DEFAULT_HORIZON_YEARS,
) -> float:
    _require_positive("current_market_cap", current_market_cap)
    _require_positive("horizon_years", horizon_years)
    if required_return <= -1 or expected_annual_dilution <= -1:
        raise ValueError("return and dilution assumptions must be greater than -100%")
    return (
        current_market_cap
        * (1 + required_return) ** horizon_years
        * (1 + expected_annual_dilution) ** horizon_years
    )


def required_future_enterprise_value(
    *,
    required_future_equity_value: float,
    terminal_net_debt: float,
) -> float:
    _require_positive("required_future_equity_value", required_future_equity_value)
    return required_future_equity_value + terminal_net_debt


def case2_required_future_revenue(
    *,
    required_future_ev: float,
    terminal_stage: TerminalStage,
    primary_metric: ValuationMetric,
    exit_multiple: float,
    target_gross_margin: float | None = None,
    target_operating_margin: float | None = None,
) -> float:
    _require_positive("required_future_ev", required_future_ev)
    _require_positive("exit_multiple", exit_multiple)

    if terminal_stage == TerminalStage.GROWTH:
        if primary_metric == ValuationMetric.EV_REVENUE:
            return required_future_ev / exit_multiple
        if primary_metric == ValuationMetric.EV_GROSS_PROFIT:
            if target_gross_margin is None or target_gross_margin <= 0:
                raise ValueError("EV/GP requires a positive target_gross_margin")
            required_gp = required_future_ev / exit_multiple
            return required_gp / target_gross_margin
        raise ValueError("GROWTH stage requires EV/Revenue or EV/GP")

    if primary_metric != ValuationMetric.EV_EBIT:
        raise ValueError("TRANSITION/MATURE stage requires EV/EBIT")
    if target_operating_margin is None or target_operating_margin <= 0:
        raise ValueError("EV/EBIT requires a positive target_operating_margin")
    required_ebit = required_future_ev / exit_multiple
    return required_ebit / target_operating_margin


def required_revenue_cagr(
    *,
    required_future_revenue: float,
    current_revenue: float,
    horizon_years: int = CASE2_DEFAULT_HORIZON_YEARS,
) -> float:
    _require_positive("required_future_revenue", required_future_revenue)
    _require_positive("current_revenue", current_revenue)
    _require_positive("horizon_years", horizon_years)
    return (required_future_revenue / current_revenue) ** (1 / horizon_years) - 1
