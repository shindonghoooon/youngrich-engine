"""Pure Case 2 Current Trend v1 calculation from comparable-period inputs."""

from __future__ import annotations

from datetime import date, datetime

from engine.case2_policy import (
    cash_burn,
    cash_burn_momentum,
    case2_fcf,
    commercial_deterioration_flag,
    commercial_inflection_flag,
    funding_runway_signal,
    funding_stress_flag,
    gross_profit_momentum,
    growth_acceleration,
    momentum_signal,
    overall_current_signal,
    thesis_kpi_momentum,
)
from engine.models import Grade
from engine.tracking_models import (
    AnalysisCase,
    BinaryEvidenceState,
    CurrentTrendSignal,
    CurrentTrendSnapshot,
    DirectionState,
    FrozenDomainModel,
    GrowthScope,
    TrendFlag,
    TrendFlagResult,
)


class Case2CurrentInput(FrozenDomainModel):
    snapshot_id: str
    ticker: str
    period_end: date
    available_at: datetime
    as_of: datetime
    growth_scope: GrowthScope
    annual_quant_grade: Grade | None
    annual_revenue_growth: float | None
    current_revenue: float | None
    prior_comparable_revenue: float | None
    current_gross_profit: float | None
    prior_comparable_gross_profit: float | None
    current_cfo: float | None
    current_growth_capex: float | None
    prior_comparable_cfo: float | None
    prior_comparable_growth_capex: float | None
    current_runway_months: float | None
    actual_shares_growth: float | None
    primary_kpi_states: tuple[DirectionState, ...]
    thesis_breaker_triggered: bool = False


def _growth(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior <= 0:
        return None
    return current / prior - 1


def _fcf(cfo: float | None, growth_capex: float | None) -> float | None:
    if cfo is None or growth_capex is None:
        return None
    return case2_fcf(cfo, growth_capex)


def build_case2_current_trend(inputs: Case2CurrentInput) -> CurrentTrendSnapshot:
    revenue_growth = _growth(inputs.current_revenue, inputs.prior_comparable_revenue)
    gross_profit_growth = _growth(
        inputs.current_gross_profit,
        inputs.prior_comparable_gross_profit,
    )
    revenue = momentum_signal(revenue_growth)
    gross_profit_result = gross_profit_momentum(
        current_gross_profit=inputs.current_gross_profit,
        prior_comparable_gross_profit=inputs.prior_comparable_gross_profit,
        yoy_growth=gross_profit_growth,
    )
    current_fcf = _fcf(inputs.current_cfo, inputs.current_growth_capex)
    prior_fcf = _fcf(inputs.prior_comparable_cfo, inputs.prior_comparable_growth_capex)
    burn = cash_burn_momentum(current_fcf, prior_fcf)
    funding = funding_runway_signal(
        inputs.current_runway_months,
        inputs.actual_shares_growth,
    )
    thesis = thesis_kpi_momentum(
        inputs.primary_kpi_states,
        thesis_breaker_triggered=inputs.thesis_breaker_triggered,
    )
    acceleration = growth_acceleration(revenue_growth, inputs.annual_revenue_growth)

    deterioration: float | None = None
    if current_fcf is not None and prior_fcf is not None:
        if current_fcf < 0 and prior_fcf >= 0:
            deterioration = float("inf")
        elif current_fcf < 0 and prior_fcf < 0 and cash_burn(prior_fcf) > 0:
            deterioration = (
                cash_burn(current_fcf) - cash_burn(prior_fcf)
            ) / cash_burn(prior_fcf)
    funding_stress = funding_stress_flag(
        deterioration,
        inputs.actual_shares_growth,
    )
    inflection = commercial_inflection_flag(
        inputs.annual_quant_grade,
        revenue,
        gross_profit_result.signal,
        thesis,
    )
    commercial_deterioration = commercial_deterioration_flag(
        inputs.annual_quant_grade,
        revenue,
        gross_profit_result.signal,
        thesis,
    )
    flags: set[TrendFlag] = set()
    if funding_stress:
        flags.add(TrendFlag.FUNDING_STRESS)
    if inflection:
        flags.add(TrendFlag.COMMERCIAL_INFLECTION)
    if commercial_deterioration:
        flags.add(TrendFlag.COMMERCIAL_DETERIORATION)
    flag_results = (
        TrendFlagResult(
            flag=TrendFlag.FUNDING_STRESS,
            state=(
                BinaryEvidenceState.UNKNOWN
                if funding_stress is None
                else BinaryEvidenceState.YES
                if funding_stress
                else BinaryEvidenceState.NO
            ),
        ),
        TrendFlagResult(
            flag=TrendFlag.COMMERCIAL_INFLECTION,
            state=(
                BinaryEvidenceState.UNKNOWN
                if inflection is None
                else BinaryEvidenceState.YES
                if inflection
                else BinaryEvidenceState.NO
            ),
        ),
        TrendFlagResult(
            flag=TrendFlag.COMMERCIAL_DETERIORATION,
            state=(
                BinaryEvidenceState.UNKNOWN
                if commercial_deterioration is None
                else BinaryEvidenceState.YES
                if commercial_deterioration
                else BinaryEvidenceState.NO
            ),
        ),
    )

    signals = (
        CurrentTrendSignal(
            name="revenue_momentum",
            state=revenue,
            observation=(
                f"yoy={revenue_growth}; acceleration={acceleration.value}; "
                f"growth_scope={inputs.growth_scope.value}"
            ),
        ),
        CurrentTrendSignal(
            name="gross_profit_momentum",
            state=gross_profit_result.signal,
            observation=gross_profit_result.warning or f"yoy={gross_profit_growth}",
        ),
        CurrentTrendSignal(
            name="cash_burn_momentum",
            state=burn,
            observation=f"prior_fcf={prior_fcf}; current_fcf={current_fcf}",
        ),
        CurrentTrendSignal(
            name="funding_runway",
            state=funding,
            observation=(
                f"runway_months={inputs.current_runway_months}; "
                f"actual_share_growth={inputs.actual_shares_growth}"
            ),
        ),
        CurrentTrendSignal(
            name="thesis_kpi_momentum",
            state=thesis,
            observation=f"resolved primary KPIs exclude unresolved inputs",
        ),
    )
    return CurrentTrendSnapshot(
        snapshot_id=inputs.snapshot_id,
        ticker=inputs.ticker,
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-current-v1-frozen",
        period_end=inputs.period_end,
        available_at=inputs.available_at,
        as_of=inputs.as_of,
        signals=signals,
        overall=overall_current_signal(tuple(signal.state for signal in signals)),
        flags=frozenset(flags),
        flag_results=flag_results,
        growth_scope=inputs.growth_scope,
        annual_quant_grade_reference=inputs.annual_quant_grade,
    )
