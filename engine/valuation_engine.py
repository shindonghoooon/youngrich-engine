"""Executable Common Valuation v1 calculations with immutable assumptions."""

from __future__ import annotations

from datetime import date, datetime

from engine.tracking_models import (
    AnalysisCase,
    AsymmetryType,
    AssumptionRange,
    ExitMultipleBand,
    FrozenDomainModel,
    RequiredGrowthCase,
    ResolutionState,
    ValuationAssumptionSet,
    ValuationSnapshot,
    ValuationOutput,
)
from engine.valuation_policy import (
    case1_required_eps_cagr,
    case2_required_future_equity_value,
    case2_required_future_revenue,
    derive_valuation_confidence,
    expectation_gap_for_ranges,
    required_future_enterprise_value,
    required_revenue_cagr,
)


class ValuationEvidenceState(FrozenDomainModel):
    credible_evidence_count: int
    company_economics_stable: bool
    company_economics_rapidly_changing: bool


class ValuationIdentity(FrozenDomainModel):
    snapshot_id: str
    ticker: str
    period_end: date
    available_at: datetime
    as_of: datetime


def _range(values: list[float]) -> AssumptionRange:
    return AssumptionRange(low=min(values), high=max(values))


def build_case1_valuation(
    *,
    identity: ValuationIdentity,
    assumptions: ValuationAssumptionSet,
    current_price: float,
    current_eps: float,
    required_return: float,
    evidence: ValuationEvidenceState,
    asymmetry_type: AsymmetryType,
) -> ValuationSnapshot:
    if assumptions.case != AnalysisCase.CASE_1_PROFITABLE_GROWTH:
        raise ValueError("Case 1 valuation requires Case 1 assumptions")
    if assumptions.primary_metric.value != "pe":
        raise ValueError("Case 1 v1 calculation engine supports PE only")
    if required_return not in assumptions.required_return_sensitivities:
        raise ValueError("required_return must be a configured sensitivity")
    cases = tuple(
        RequiredGrowthCase(
            band=multiple.band,
            exit_multiple=multiple.value,
            required_growth=case1_required_eps_cagr(
                current_price=current_price,
                current_eps=current_eps,
                exit_pe=multiple.value,
                required_return=required_return,
                horizon_years=assumptions.horizon_years,
            ),
        )
        for multiple in assumptions.exit_multiples
    )
    growth_range = _range([case.required_growth for case in cases])
    confidence = derive_valuation_confidence(
        credible_evidence_count=evidence.credible_evidence_count,
        company_economics_stable=evidence.company_economics_stable,
        company_economics_rapidly_changing=evidence.company_economics_rapidly_changing,
        terminal_stage_confidence=assumptions.terminal_stage_confidence,
    )
    base_growth = next(
        case.required_growth for case in cases if case.band == ExitMultipleBand.BASE
    )
    output = ValuationOutput(
        required_growth=base_growth,
        required_growth_range=growth_range,
        required_growth_cases=cases,
        expectation_gap=expectation_gap_for_ranges(
            required=growth_range,
            plausible=assumptions.plausible_growth_range,
        ),
        asymmetry_type=asymmetry_type,
        confidence=confidence,
    )
    return ValuationSnapshot(
        **identity.model_dump(),
        assumption_set=assumptions,
        state=ResolutionState.RESOLVED,
        market_price=current_price,
        output=output,
    )


def build_case2_valuation(
    *,
    identity: ValuationIdentity,
    assumptions: ValuationAssumptionSet,
    current_market_cap: float,
    current_revenue: float,
    required_return: float,
    evidence: ValuationEvidenceState,
    asymmetry_type: AsymmetryType,
) -> ValuationSnapshot:
    if assumptions.case != AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH:
        raise ValueError("Case 2 valuation requires Case 2 assumptions")
    if required_return not in assumptions.required_return_sensitivities:
        raise ValueError("required_return must be a configured sensitivity")
    future_equity = case2_required_future_equity_value(
        current_market_cap=current_market_cap,
        required_return=required_return,
        expected_annual_dilution=assumptions.expected_annual_dilution,
        horizon_years=assumptions.horizon_years,
    )
    future_ev = required_future_enterprise_value(
        required_future_equity_value=future_equity,
        terminal_net_debt=assumptions.terminal_net_debt,
    )
    results: list[RequiredGrowthCase] = []
    for multiple in assumptions.exit_multiples:
        revenue = case2_required_future_revenue(
            required_future_ev=future_ev,
            terminal_stage=assumptions.terminal_stage,
            primary_metric=assumptions.primary_metric,
            exit_multiple=multiple.value,
            target_gross_margin=assumptions.target_gross_margin,
            target_operating_margin=assumptions.target_operating_margin,
        )
        growth = required_revenue_cagr(
            required_future_revenue=revenue,
            current_revenue=current_revenue,
            horizon_years=assumptions.horizon_years,
        )
        results.append(
            RequiredGrowthCase(
                band=multiple.band,
                exit_multiple=multiple.value,
                required_growth=growth,
                required_future_equity_value=future_equity,
                required_future_enterprise_value=future_ev,
                required_future_revenue=revenue,
            )
        )
    cases = tuple(results)
    growth_range = _range([case.required_growth for case in cases])
    confidence = derive_valuation_confidence(
        credible_evidence_count=evidence.credible_evidence_count,
        company_economics_stable=evidence.company_economics_stable,
        company_economics_rapidly_changing=evidence.company_economics_rapidly_changing,
        terminal_stage_confidence=assumptions.terminal_stage_confidence,
    )
    base_growth = next(
        case.required_growth for case in cases if case.band == ExitMultipleBand.BASE
    )
    output = ValuationOutput(
        required_growth=base_growth,
        required_growth_range=growth_range,
        required_growth_cases=cases,
        expectation_gap=expectation_gap_for_ranges(
            required=growth_range,
            plausible=assumptions.plausible_growth_range,
        ),
        asymmetry_type=asymmetry_type,
        confidence=confidence,
    )
    return ValuationSnapshot(
        **identity.model_dump(),
        assumption_set=assumptions,
        state=ResolutionState.RESOLVED,
        market_cap=current_market_cap,
        output=output,
    )
