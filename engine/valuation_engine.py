"""Executable Common Valuation v1 calculations with immutable assumptions."""

from __future__ import annotations

import json
from datetime import date, datetime
from hashlib import sha256
from typing import Self

from pydantic import model_validator

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
    validate_valuation_evidence_timing,
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
    available_at: datetime
    retrieved_at: datetime | None = None

    @model_validator(mode="after")
    def validate_available_at(self) -> Self:
        if self.available_at.tzinfo is None or self.available_at.utcoffset() is None:
            raise ValueError("valuation evidence available_at must be timezone-aware")
        if self.retrieved_at is not None and (
            self.retrieved_at.tzinfo is None
            or self.retrieved_at.utcoffset() is None
        ):
            raise ValueError("valuation evidence retrieved_at must be timezone-aware")
        return self


class ValuationIdentity(FrozenDomainModel):
    snapshot_id: str
    ticker: str
    period_end: date
    available_at: datetime
    as_of: datetime


VALUATION_INPUT_FINGERPRINT_VERSION = "valuation-input-v1"


def valuation_input_fingerprint(
    *,
    identity: ValuationIdentity,
    current_eps: float | None = None,
    current_revenue: float | None = None,
    current_share_count: float | None = None,
) -> str:
    """Hash deterministic fundamental valuation inputs, never price or run metadata."""
    if current_eps is None and current_revenue is None:
        raise ValueError("a valuation fundamental input is required")
    payload = {
        "version": VALUATION_INPUT_FINGERPRINT_VERSION,
        "ticker": identity.ticker,
        "period_end": identity.period_end.isoformat(),
        "current_eps": current_eps,
        "current_revenue": current_revenue,
        "current_share_count": current_share_count,
        "accounting_scope": "reported_gaap",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


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
    validate_valuation_evidence_timing(
        evaluation_as_of=identity.as_of,
        assumption_set=assumptions,
        evidence_available_at=evidence.available_at,
        evidence_retrieved_at=evidence.retrieved_at,
        require_evidence_available_at=True,
    )
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
        fundamental_input_fingerprint=valuation_input_fingerprint(
            identity=identity,
            current_eps=current_eps,
        ),
        evidence_available_at=evidence.available_at,
        evidence_retrieved_at=evidence.retrieved_at,
        output=output,
    )


def build_case2_valuation(
    *,
    identity: ValuationIdentity,
    assumptions: ValuationAssumptionSet,
    current_market_cap: float,
    current_price: float,
    current_revenue: float,
    current_share_count: float,
    required_return: float,
    evidence: ValuationEvidenceState,
    asymmetry_type: AsymmetryType,
) -> ValuationSnapshot:
    if assumptions.case != AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH:
        raise ValueError("Case 2 valuation requires Case 2 assumptions")
    if required_return not in assumptions.required_return_sensitivities:
        raise ValueError("required_return must be a configured sensitivity")
    if current_share_count <= 0:
        raise ValueError("current_share_count must be positive")
    if current_price <= 0:
        raise ValueError("current_price must be positive")
    validate_valuation_evidence_timing(
        evaluation_as_of=identity.as_of,
        assumption_set=assumptions,
        evidence_available_at=evidence.available_at,
        evidence_retrieved_at=evidence.retrieved_at,
        require_evidence_available_at=True,
    )
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
        market_price=current_price,
        market_cap=current_market_cap,
        fundamental_input_fingerprint=valuation_input_fingerprint(
            identity=identity,
            current_revenue=current_revenue,
            current_share_count=current_share_count,
        ),
        evidence_available_at=evidence.available_at,
        evidence_retrieved_at=evidence.retrieved_at,
        output=output,
    )
