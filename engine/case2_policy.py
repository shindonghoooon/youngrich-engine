"""Frozen Case 2 v1 policy functions.

The module encodes the authoritative specification without performing ingestion,
company-specific normalization, valuation, or Investment Grade calculation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from math import isclose

from pydantic import BaseModel, ConfigDict

from engine.models import Grade
from engine.tracking_models import (
    DirectionState,
    NarrativeGate,
    NarrativeState,
    ResolutionState,
)


CASE2_CORE_WEIGHTS = {
    "revenue_growth": 0.30,
    "gross_profit_growth": 0.15,
    "cash_burn_trend": 0.15,
    "runway": 0.15,
    "dilution": 0.15,
    "revenue_per_share_growth": 0.10,
}
CASE2_MANDATORY_METRICS = frozenset(
    {"revenue_growth", "gross_profit_growth", "cash_burn_trend", "runway"}
)
CASE2_SHAREHOLDER_OPTIONAL_METRICS = frozenset(
    {"dilution", "revenue_per_share_growth"}
)
GRADE_POINTS = {Grade.A: 4, Grade.B: 3, Grade.C: 2, Grade.D: 1, Grade.X: 0}
_GRADE_ORDER = {Grade.A: 0, Grade.B: 1, Grade.C: 2, Grade.D: 3, Grade.X: 4}


class EligibilityState(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNRESOLVED = "unresolved"


class AccelerationState(str, Enum):
    ACCELERATING = "accelerating"
    STABLE = "stable"
    DECELERATING = "decelerating"
    UNRESOLVED = "unresolved"


class Case2QuantEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: ResolutionState
    raw_score: float | None
    uncapped_grade: Grade | None
    final_grade: Grade | None
    coverage: float
    provisional: bool
    funding_stress_cap_applied: bool


class IncrementalMarginResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float | None
    scaling_failure: bool


class MomentumResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    signal: DirectionState
    warning: str | None = None


def case2_eligibility(
    *,
    core_business_revenue: float | None,
    gross_profit: float | None,
    operating_income: float | None,
    core_revenue_representative: bool | None,
    commercial_evidence_exists: bool | None,
) -> EligibilityState:
    inputs = (
        core_business_revenue,
        gross_profit,
        operating_income,
        core_revenue_representative,
        commercial_evidence_exists,
    )
    if any(value is None for value in inputs):
        return EligibilityState.UNRESOLVED
    if (
        core_business_revenue > 0
        and gross_profit > 0
        and operating_income < 0
        and core_revenue_representative
        and commercial_evidence_exists
    ):
        return EligibilityState.ELIGIBLE
    return EligibilityState.INELIGIBLE


def _grade_by_thresholds(
    value: float | None,
    thresholds: tuple[tuple[float, Grade], ...],
) -> Grade | None:
    if value is None:
        return None
    for threshold, grade in thresholds:
        if value >= threshold:
            return grade
    return Grade.X


def cagr_2y(latest: float | None, two_years_ago: float | None) -> float | None:
    if latest is None or two_years_ago is None:
        return None
    if latest <= 0 or two_years_ago <= 0:
        return None
    return (latest / two_years_ago) ** 0.5 - 1


def grade_revenue_growth(value: float | None) -> Grade | None:
    return _grade_by_thresholds(
        value,
        ((0.40, Grade.A), (0.25, Grade.B), (0.15, Grade.C), (0.0, Grade.D)),
    )


def grade_gross_profit_growth(value: float | None) -> Grade | None:
    return _grade_by_thresholds(
        value,
        ((0.45, Grade.A), (0.30, Grade.B), (0.15, Grade.C), (0.0, Grade.D)),
    )


def growth_capex(
    ppe_purchases: float,
    capitalized_internal_use_software: float = 0.0,
    capitalized_product_software: float = 0.0,
) -> float:
    values = (
        ppe_purchases,
        capitalized_internal_use_software,
        capitalized_product_software,
    )
    if any(value < 0 for value in values):
        raise ValueError("Growth CAPEX components must be non-negative cash outflows")
    return sum(values)


def case2_fcf(cfo: float, normalized_growth_capex: float) -> float:
    if normalized_growth_capex < 0:
        raise ValueError("normalized Growth CAPEX must be non-negative")
    return cfo - normalized_growth_capex


def cash_burn(fcf: float) -> float:
    return max(0.0, -fcf)


def grade_cash_burn_trend(
    latest_fcf: float | None,
    previous_fcf: float | None,
) -> Grade | None:
    if latest_fcf is None or previous_fcf is None:
        return None
    if latest_fcf >= 0:
        return Grade.A
    if previous_fcf >= 0:
        return Grade.X

    previous_burn = cash_burn(previous_fcf)
    latest_burn = cash_burn(latest_fcf)
    if previous_burn == 0:
        return None

    burn_reduction = (previous_burn - latest_burn) / previous_burn
    if burn_reduction >= 0.30:
        return Grade.A
    if burn_reduction >= 0.10:
        return Grade.B

    burn_increase = (latest_burn - previous_burn) / previous_burn
    if burn_increase <= 0.10:
        return Grade.C
    if burn_increase <= 0.50:
        return Grade.D
    return Grade.X


def runway_months(liquidity: float | None, latest_fcf: float | None) -> float | None:
    if latest_fcf is None:
        return None
    if latest_fcf >= 0:
        return float("inf")
    if liquidity is None:
        return None
    if liquidity < 0:
        raise ValueError("liquidity cannot be negative")
    return liquidity / cash_burn(latest_fcf) * 12


def grade_runway(liquidity: float | None, latest_fcf: float | None) -> Grade | None:
    months = runway_months(liquidity, latest_fcf)
    if months is None:
        return None
    if months >= 36:
        return Grade.A
    if months >= 24:
        return Grade.B
    if months >= 12:
        return Grade.C
    if months >= 6:
        return Grade.D
    return Grade.X


def actual_share_growth(
    latest_actual_shares: float | None,
    prior_actual_shares: float | None,
) -> float | None:
    if latest_actual_shares is None or prior_actual_shares is None:
        return None
    if latest_actual_shares <= 0 or prior_actual_shares <= 0:
        return None
    return latest_actual_shares / prior_actual_shares - 1


def grade_dilution(value: float | None) -> Grade | None:
    if value is None:
        return None
    if value <= 0.02:
        return Grade.A
    if value <= 0.05:
        return Grade.B
    if value <= 0.10:
        return Grade.C
    if value <= 0.20:
        return Grade.D
    return Grade.X


def revenue_per_share_growth(
    latest_revenue: float | None,
    latest_actual_shares: float | None,
    prior_revenue: float | None,
    prior_actual_shares: float | None,
) -> float | None:
    values = (
        latest_revenue,
        latest_actual_shares,
        prior_revenue,
        prior_actual_shares,
    )
    if any(value is None or value <= 0 for value in values):
        return None
    latest_per_share = latest_revenue / latest_actual_shares
    prior_per_share = prior_revenue / prior_actual_shares
    return latest_per_share / prior_per_share - 1


def grade_revenue_per_share_growth(value: float | None) -> Grade | None:
    return _grade_by_thresholds(
        value,
        ((0.30, Grade.A), (0.20, Grade.B), (0.10, Grade.C), (0.0, Grade.D)),
    )


def incremental_operating_margin(
    latest_revenue: float,
    prior_revenue: float,
    latest_operating_income: float,
    prior_operating_income: float,
) -> IncrementalMarginResult:
    revenue_change = latest_revenue - prior_revenue
    if revenue_change <= 0:
        return IncrementalMarginResult(value=None, scaling_failure=True)
    return IncrementalMarginResult(
        value=(latest_operating_income - prior_operating_income) / revenue_change,
        scaling_failure=False,
    )


def quant_grade(score: float) -> Grade:
    if score >= 3.50:
        return Grade.A
    if score >= 3.00:
        return Grade.B
    if score >= 2.40:
        return Grade.C
    if score >= 1.80:
        return Grade.D
    return Grade.X


def _cap_grade(grade: Grade, maximum_grade: Grade) -> Grade:
    if _GRADE_ORDER[grade] < _GRADE_ORDER[maximum_grade]:
        return maximum_grade
    return grade


def evaluate_case2_quant(
    metric_grades: Mapping[str, Grade | None],
) -> Case2QuantEvaluation:
    if set(metric_grades) != set(CASE2_CORE_WEIGHTS):
        raise ValueError("metric_grades must contain exactly the frozen Case 2 Core 6")

    resolved_weight = sum(
        CASE2_CORE_WEIGHTS[name]
        for name, grade in metric_grades.items()
        if grade is not None
    )
    coverage = resolved_weight / sum(CASE2_CORE_WEIGHTS.values())
    if any(metric_grades[name] is None for name in CASE2_MANDATORY_METRICS):
        return Case2QuantEvaluation(
            state=ResolutionState.UNRESOLVED,
            raw_score=None,
            uncapped_grade=None,
            final_grade=None,
            coverage=coverage,
            provisional=False,
            funding_stress_cap_applied=False,
        )

    unresolved = {name for name, grade in metric_grades.items() if grade is None}
    if not unresolved.issubset(CASE2_SHAREHOLDER_OPTIONAL_METRICS):
        raise ValueError("only shareholder metrics may use provisional coverage")

    raw_score = sum(
        GRADE_POINTS[grade] * CASE2_CORE_WEIGHTS[name]
        for name, grade in metric_grades.items()
        if grade is not None
    ) / resolved_weight
    uncapped = quant_grade(raw_score)
    cap_applied = (
        metric_grades["cash_burn_trend"] == Grade.X
        and metric_grades["dilution"] == Grade.X
    )
    final = _cap_grade(uncapped, Grade.D) if cap_applied else uncapped
    return Case2QuantEvaluation(
        state=ResolutionState.RESOLVED,
        raw_score=raw_score,
        uncapped_grade=uncapped,
        final_grade=final,
        coverage=coverage,
        provisional=coverage < 1.0,
        funding_stress_cap_applied=cap_applied,
    )


def momentum_signal(growth: float | None) -> DirectionState:
    if growth is None:
        return DirectionState.UNRESOLVED
    if growth >= 0.25:
        return DirectionState.POSITIVE
    if growth >= 0.10:
        return DirectionState.NEUTRAL
    return DirectionState.NEGATIVE


def growth_acceleration(
    current_growth: float | None,
    annual_base_growth: float | None,
) -> AccelerationState:
    if current_growth is None or annual_base_growth is None:
        return AccelerationState.UNRESOLVED
    difference = current_growth - annual_base_growth
    if difference > 0.10 or isclose(difference, 0.10, abs_tol=1e-12):
        return AccelerationState.ACCELERATING
    if difference < -0.10 or isclose(difference, -0.10, abs_tol=1e-12):
        return AccelerationState.DECELERATING
    return AccelerationState.STABLE


def thesis_kpi_momentum(
    primary_kpi_states: Sequence[DirectionState],
    *,
    thesis_breaker_triggered: bool,
) -> DirectionState:
    if thesis_breaker_triggered:
        return DirectionState.NEGATIVE
    resolved = [
        state
        for state in primary_kpi_states
        if state != DirectionState.UNRESOLVED
    ]
    if len(resolved) < 2:
        return DirectionState.UNRESOLVED
    improving = resolved.count(DirectionState.POSITIVE)
    deteriorating = resolved.count(DirectionState.NEGATIVE)
    if improving > deteriorating:
        return DirectionState.POSITIVE
    if deteriorating > improving:
        return DirectionState.NEGATIVE
    return DirectionState.NEUTRAL


def gross_profit_momentum(
    *,
    current_gross_profit: float | None,
    prior_comparable_gross_profit: float | None,
    yoy_growth: float | None,
) -> MomentumResult:
    if current_gross_profit is None or prior_comparable_gross_profit is None:
        return MomentumResult(signal=DirectionState.UNRESOLVED)
    if current_gross_profit < 0 <= prior_comparable_gross_profit:
        return MomentumResult(
            signal=DirectionState.NEGATIVE,
            warning="gross profit turned negative",
        )
    return MomentumResult(signal=momentum_signal(yoy_growth))


def cash_burn_momentum(
    current_fcf: float | None,
    prior_comparable_fcf: float | None,
) -> DirectionState:
    if current_fcf is None or prior_comparable_fcf is None:
        return DirectionState.UNRESOLVED
    if current_fcf >= 0:
        return DirectionState.POSITIVE
    if prior_comparable_fcf >= 0:
        return DirectionState.NEGATIVE

    previous_burn = cash_burn(prior_comparable_fcf)
    if previous_burn == 0:
        return DirectionState.UNRESOLVED
    change = (cash_burn(current_fcf) - previous_burn) / previous_burn
    if change <= -0.20:
        return DirectionState.POSITIVE
    if change <= 0.20:
        return DirectionState.NEUTRAL
    return DirectionState.NEGATIVE


def funding_runway_signal(
    current_runway_months: float | None,
    actual_shares_growth: float | None,
) -> DirectionState:
    if current_runway_months is None or actual_shares_growth is None:
        return DirectionState.UNRESOLVED
    if current_runway_months >= 24 and actual_shares_growth <= 0.05:
        return DirectionState.POSITIVE
    if current_runway_months >= 12 and actual_shares_growth <= 0.15:
        return DirectionState.NEUTRAL
    return DirectionState.NEGATIVE


def funding_stress_flag(
    cash_burn_deterioration: float | None,
    actual_shares_growth: float | None,
) -> bool | None:
    if cash_burn_deterioration is None or actual_shares_growth is None:
        return None
    return cash_burn_deterioration > 0.50 and actual_shares_growth > 0.20


def overall_current_signal(signals: Sequence[DirectionState]) -> DirectionState:
    allowed = {
        DirectionState.POSITIVE,
        DirectionState.NEUTRAL,
        DirectionState.NEGATIVE,
        DirectionState.UNRESOLVED,
    }
    if any(signal not in allowed for signal in signals):
        raise ValueError("overall input must contain only Case 2 sub-signal states")
    resolved = [signal for signal in signals if signal != DirectionState.UNRESOLVED]
    if len(resolved) < 4:
        return DirectionState.UNRESOLVED
    positive = resolved.count(DirectionState.POSITIVE)
    negative = resolved.count(DirectionState.NEGATIVE)
    if positive >= 4 and negative == 0:
        return DirectionState.STRONG_POSITIVE
    if positive >= 2 and negative >= 2:
        return DirectionState.MIXED
    if positive >= 3 and negative <= 1:
        return DirectionState.POSITIVE
    if negative >= 3 and positive <= 1:
        return DirectionState.NEGATIVE
    return DirectionState.NEUTRAL


def commercial_inflection_flag(
    annual_quant_grade: Grade | None,
    revenue_momentum: DirectionState,
    gross_profit_momentum: DirectionState,
    thesis_kpi_momentum: DirectionState,
) -> bool | None:
    states = (revenue_momentum, gross_profit_momentum, thesis_kpi_momentum)
    if annual_quant_grade is None or DirectionState.UNRESOLVED in states:
        return None
    weak_or_unresolved = annual_quant_grade in {Grade.D, Grade.X}
    return weak_or_unresolved and all(
        signal == DirectionState.POSITIVE
        for signal in (
            revenue_momentum,
            gross_profit_momentum,
            thesis_kpi_momentum,
        )
    )


def commercial_deterioration_flag(
    annual_quant_grade: Grade | None,
    revenue_momentum: DirectionState,
    gross_profit_momentum: DirectionState,
    thesis_kpi_momentum: DirectionState,
) -> bool | None:
    states = (revenue_momentum, gross_profit_momentum, thesis_kpi_momentum)
    if annual_quant_grade is None or DirectionState.UNRESOLVED in states:
        return None
    return annual_quant_grade in {Grade.A, Grade.B} and all(
        signal == DirectionState.NEGATIVE
        for signal in (
            revenue_momentum,
            gross_profit_momentum,
            thesis_kpi_momentum,
        )
    )


def derive_narrative_gate(
    *,
    differentiation: NarrativeState,
    defensibility: NarrativeState,
    adoption: NarrativeState,
    durability: NarrativeState,
    commercial_evidence_exists: bool,
    thesis_breaker_triggered: bool,
    core_evidence_damaged: bool = False,
) -> NarrativeGate:
    if thesis_breaker_triggered:
        return NarrativeGate.BROKEN
    if adoption == NarrativeState.WEAK or core_evidence_damaged:
        return NarrativeGate.WEAK
    if not commercial_evidence_exists:
        return NarrativeGate.UNRESOLVED

    strong = {NarrativeState.STRONG, NarrativeState.PROVEN}
    durable = {NarrativeState.EMERGING, *strong}
    differentiated_or_defensible = (
        differentiation in strong or defensibility in strong
    )
    if adoption in strong and durability in strong and differentiated_or_defensible:
        return NarrativeGate.CONFIRMED
    if adoption in strong and durability in durable and differentiated_or_defensible:
        return NarrativeGate.QUALIFIED
    return NarrativeGate.DEVELOPING
