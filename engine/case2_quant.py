"""Deterministic Case 2 Quant v1 calculation from normalized annual inputs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import Field, model_validator

from engine.annual_periods import validate_annual_periods
from engine.case2_policy import (
    CASE2_CORE_WEIGHTS,
    CASE2_SHAREHOLDER_OPTIONAL_METRICS,
    EligibilityState,
    actual_share_growth,
    cagr_2y,
    case2_eligibility,
    case2_fcf,
    evaluate_case2_quant,
    grade_cash_burn_trend,
    grade_dilution,
    grade_gross_profit_growth,
    grade_revenue_growth,
    grade_revenue_per_share_growth,
    grade_runway,
    incremental_operating_margin,
    revenue_per_share_growth,
    runway_months,
)
from engine.models import Grade, Trend
from engine.tracking_models import (
    AnalysisCase,
    FrozenDomainModel,
    GradeCap,
    GrowthScope,
    MetricResult,
    QuantSnapshot,
    ResolutionState,
)


class Case2AnnualPeriod(FrozenDomainModel):
    fiscal_year: int
    fiscal_period_end: date
    revenue: float | None
    gross_profit: float | None
    operating_income: float | None
    cfo: float | None
    growth_capex: float | None
    liquidity: float | None
    actual_common_shares: float | None


class Case2QuantInput(FrozenDomainModel):
    snapshot_id: str
    ticker: str
    periods: tuple[Case2AnnualPeriod, ...] = Field(min_length=3)
    period_end: date
    available_at: datetime
    as_of: datetime
    growth_scope: GrowthScope
    core_revenue_representative: bool | None
    commercial_evidence_exists: bool | None
    share_comparison_valid: bool = True
    potential_dilution: float | str | None = None

    @model_validator(mode="after")
    def validate_periods(self) -> Self:
        ordered = tuple(sorted(self.periods, key=lambda period: period.fiscal_period_end))
        if self.periods != ordered:
            raise ValueError("periods must be sorted by fiscal_period_end")
        if self.period_end != self.periods[-1].fiscal_period_end:
            raise ValueError("period_end must match the latest annual period")
        validate_annual_periods(self.periods)
        return self


class Case2QuantResult(FrozenDomainModel):
    eligibility: EligibilityState
    snapshot: QuantSnapshot


def validate_case2_quant_snapshot(
    snapshot: QuantSnapshot,
    *,
    allow_missing: bool = False,
) -> tuple[str, ...]:
    """Validate Core 6 and optionally report genuine omissions for an IG U gate."""
    by_name = {metric.name: metric for metric in snapshot.metrics}
    core = tuple(metric for metric in snapshot.metrics if metric.is_core)
    names = [metric.name for metric in core]
    if len(names) != len(set(names)) or set(names) - set(CASE2_CORE_WEIGHTS):
        raise ValueError("Case 2 Quant requires exactly the frozen Core 6")
    for name in set(CASE2_CORE_WEIGHTS) & set(by_name):
        if not by_name[name].is_core:
            raise ValueError(f"required Quant metric cannot be supporting: {name}")
    for metric in core:
        if abs(metric.weight - CASE2_CORE_WEIGHTS[metric.name]) > 1e-12:
            raise ValueError("Case 2 Core metric weight does not match frozen policy")
        if metric.state == ResolutionState.RESOLVED and metric.grade is None:
            raise ValueError("resolved Case 2 Core metric requires a grade")
        if metric.state == ResolutionState.UNRESOLVED and (
            metric.value is not None or metric.grade is not None
        ):
            raise ValueError("unresolved Case 2 Core metric cannot carry value or grade")
    missing = tuple(sorted(set(CASE2_CORE_WEIGHTS) - set(names)))
    if missing and not allow_missing:
        raise ValueError("Case 2 Quant requires exactly the frozen Core 6")
    unresolved = {
        metric.name for metric in core if metric.state == ResolutionState.UNRESOLVED
    }
    if unresolved - CASE2_SHAREHOLDER_OPTIONAL_METRICS:
        if snapshot.state == ResolutionState.RESOLVED:
            raise ValueError("mandatory Case 2 Core metrics cannot be unresolved")
    if snapshot.state == ResolutionState.RESOLVED and unresolved:
        if not snapshot.provisional:
            raise ValueError("shareholder-comparability exception must be provisional")
        if not unresolved.issubset(CASE2_SHAREHOLDER_OPTIONAL_METRICS):
            raise ValueError("only shareholder metrics may be unresolved provisionally")
    return missing


def _fcf(period: Case2AnnualPeriod) -> float | None:
    if period.cfo is None or period.growth_capex is None:
        return None
    return case2_fcf(period.cfo, period.growth_capex)


def _metric(
    *,
    name: str,
    value: float | str | None,
    grade: Grade | None,
    unit: str,
    note: str | None = None,
) -> MetricResult:
    state = ResolutionState.RESOLVED if value is not None else ResolutionState.UNRESOLVED
    return MetricResult(
        name=name,
        state=state,
        value=value,
        unit=unit if value is not None else None,
        grade=grade,
        trend=Trend.NA,
        weight=CASE2_CORE_WEIGHTS[name],
        note=note,
    )


def _cash_burn_observation(
    latest_fcf: float | None,
    previous_fcf: float | None,
) -> float | str | None:
    if latest_fcf is None or previous_fcf is None:
        return None
    if latest_fcf >= 0 and previous_fcf < 0:
        return "burning_to_positive"
    if latest_fcf < 0 and previous_fcf >= 0:
        return "positive_to_burning"
    if latest_fcf >= 0:
        return "fcf_positive"
    return ((-latest_fcf) - (-previous_fcf)) / (-previous_fcf)


def build_case2_quant(inputs: Case2QuantInput) -> Case2QuantResult:
    first = inputs.periods[-3]
    previous = inputs.periods[-2]
    latest = inputs.periods[-1]
    latest_fcf = _fcf(latest)
    previous_fcf = _fcf(previous)

    eligibility = case2_eligibility(
        core_business_revenue=latest.revenue,
        gross_profit=latest.gross_profit,
        operating_income=latest.operating_income,
        core_revenue_representative=inputs.core_revenue_representative,
        commercial_evidence_exists=inputs.commercial_evidence_exists,
    )
    revenue_growth = cagr_2y(latest.revenue, first.revenue)
    gross_profit_growth = cagr_2y(latest.gross_profit, first.gross_profit)
    runway = runway_months(latest.liquidity, latest_fcf)
    dilution = (
        actual_share_growth(latest.actual_common_shares, previous.actual_common_shares)
        if inputs.share_comparison_valid
        else None
    )
    per_share_growth = (
        revenue_per_share_growth(
            latest.revenue,
            latest.actual_common_shares,
            previous.revenue,
            previous.actual_common_shares,
        )
        if inputs.share_comparison_valid
        else None
    )

    core = (
        _metric(
            name="revenue_growth",
            value=revenue_growth,
            grade=grade_revenue_growth(revenue_growth),
            unit="ratio",
        ),
        _metric(
            name="gross_profit_growth",
            value=gross_profit_growth,
            grade=grade_gross_profit_growth(gross_profit_growth),
            unit="ratio",
        ),
        _metric(
            name="cash_burn_trend",
            value=_cash_burn_observation(latest_fcf, previous_fcf),
            grade=grade_cash_burn_trend(latest_fcf, previous_fcf),
            unit="burn_change_ratio_or_transition",
            note=f"previous_fcf={previous_fcf}; latest_fcf={latest_fcf}",
        ),
        _metric(
            name="runway",
            value=runway,
            grade=grade_runway(latest.liquidity, latest_fcf),
            unit="months",
        ),
        _metric(
            name="dilution",
            value=dilution,
            grade=grade_dilution(dilution),
            unit="ratio",
            note=None if inputs.share_comparison_valid else "share comparison unresolved",
        ),
        _metric(
            name="revenue_per_share_growth",
            value=per_share_growth,
            grade=grade_revenue_per_share_growth(per_share_growth),
            unit="ratio",
            note=None if inputs.share_comparison_valid else "share comparison unresolved",
        ),
    )
    grade_map = {metric.name: metric.grade for metric in core}
    evaluation = evaluate_case2_quant(grade_map)

    margin = (
        latest.gross_profit / latest.revenue
        if latest.gross_profit is not None and latest.revenue and latest.revenue > 0
        else None
    )
    prior_margin = (
        previous.gross_profit / previous.revenue
        if previous.gross_profit is not None
        and previous.revenue
        and previous.revenue > 0
        else None
    )
    margin_change = margin - prior_margin if margin is not None and prior_margin is not None else None
    incremental = (
        incremental_operating_margin(
            latest.revenue,
            previous.revenue,
            latest.operating_income,
            previous.operating_income,
        )
        if all(
            value is not None
            for value in (
                latest.revenue,
                previous.revenue,
                latest.operating_income,
                previous.operating_income,
            )
        )
        else None
    )
    supporting = (
        MetricResult(
            name="gross_margin_trend",
            state=ResolutionState.RESOLVED if margin_change is not None else ResolutionState.UNRESOLVED,
            value=margin_change,
            unit="pct_point" if margin_change is not None else None,
            weight=0,
            is_core=False,
        ),
        MetricResult(
            name="incremental_operating_margin",
            state=(
                ResolutionState.RESOLVED
                if incremental is not None and incremental.value is not None
                else ResolutionState.UNRESOLVED
            ),
            value=incremental.value if incremental is not None else None,
            unit="ratio" if incremental is not None and incremental.value is not None else None,
            weight=0,
            is_core=False,
            supporting_tags=("scaling_failure",) if incremental is not None and incremental.scaling_failure else (),
        ),
        MetricResult(
            name="potential_dilution",
            state=(
                ResolutionState.RESOLVED
                if inputs.potential_dilution is not None
                else ResolutionState.UNRESOLVED
            ),
            value=inputs.potential_dilution,
            weight=0,
            is_core=False,
        ),
        MetricResult(
            name="growth_scope",
            state=(
                ResolutionState.UNRESOLVED
                if inputs.growth_scope == GrowthScope.UNRESOLVED
                else ResolutionState.RESOLVED
            ),
            value=(
                None
                if inputs.growth_scope == GrowthScope.UNRESOLVED
                else inputs.growth_scope.value
            ),
            weight=0,
            is_core=False,
        ),
    )

    eligible_and_resolved = (
        eligibility == EligibilityState.ELIGIBLE
        and evaluation.state == ResolutionState.RESOLVED
    )
    caps = (
        (
            GradeCap(
                trigger="cash_burn_x_and_dilution_x",
                maximum_grade=Grade.D,
                active=True,
                reason="Case 2 Quant v1 Cash Burn X + Dilution X guardrail",
            ),
        )
        if evaluation.funding_stress_cap_applied
        and eligibility == EligibilityState.ELIGIBLE
        else ()
    )
    snapshot = QuantSnapshot(
        snapshot_id=inputs.snapshot_id,
        ticker=inputs.ticker,
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-quant-v1-frozen",
        period_end=inputs.period_end,
        available_at=inputs.available_at,
        as_of=inputs.as_of,
        metrics=core + supporting,
        state=(ResolutionState.RESOLVED if eligible_and_resolved else ResolutionState.UNRESOLVED),
        score=evaluation.raw_score if eligible_and_resolved else None,
        uncapped_grade=evaluation.uncapped_grade if eligible_and_resolved else None,
        grade=evaluation.final_grade if eligible_and_resolved else None,
        grade_caps=caps,
        growth_scope=inputs.growth_scope,
        coverage=evaluation.coverage,
        provisional=evaluation.provisional if eligible_and_resolved else False,
    )
    validate_case2_quant_snapshot(snapshot)
    return Case2QuantResult(eligibility=eligibility, snapshot=snapshot)
