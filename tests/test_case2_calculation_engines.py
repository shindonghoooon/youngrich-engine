from datetime import date, datetime, timezone

import pytest

from engine.case2_current import Case2CurrentInput, build_case2_current_trend
from engine.case2_policy import (
    AccelerationState,
    EligibilityState,
    cash_burn_momentum,
    funding_runway_signal,
    gross_profit_momentum,
    growth_acceleration,
    momentum_signal,
    thesis_kpi_momentum,
)
from engine.case2_quant import Case2AnnualPeriod, Case2QuantInput, build_case2_quant
from engine.models import Grade
from engine.narrative_engine import derive_gate_from_snapshot
from engine.tracking_models import (
    AnalysisCase,
    DirectionState,
    GrowthScope,
    NarrativeAssessment,
    NarrativeGate,
    NarrativeSnapshot,
    NarrativeState,
    ResolutionState,
    TrendFlag,
)


UTC = timezone.utc
AS_OF = datetime(2026, 4, 1, tzinfo=UTC)
AVAILABLE = datetime(2026, 2, 15, tzinfo=UTC)


def annual_period(
    year: int,
    *,
    revenue: float | None,
    gross_profit: float | None,
    operating_income: float | None = -10,
    cfo: float | None = -10,
    growth_capex: float | None = 10,
    liquidity: float | None = 100,
    shares: float | None = 100,
) -> Case2AnnualPeriod:
    return Case2AnnualPeriod(
        fiscal_year=year,
        fiscal_period_end=date(year, 12, 31),
        revenue=revenue,
        gross_profit=gross_profit,
        operating_income=operating_income,
        cfo=cfo,
        growth_capex=growth_capex,
        liquidity=liquidity,
        actual_common_shares=shares,
    )


def quant_input(
    periods: tuple[Case2AnnualPeriod, ...],
    *,
    share_comparison_valid: bool = True,
    growth_scope: GrowthScope = GrowthScope.SAME_SCOPE,
    potential_dilution: float | str | None = 0.12,
) -> Case2QuantInput:
    return Case2QuantInput(
        snapshot_id="case2-quant-synthetic",
        ticker="SYNTH",
        periods=periods,
        period_end=periods[-1].fiscal_period_end,
        available_at=AVAILABLE,
        as_of=AS_OF,
        growth_scope=growth_scope,
        core_revenue_representative=True,
        commercial_evidence_exists=True,
        share_comparison_valid=share_comparison_valid,
        potential_dilution=potential_dilution,
    )


def test_case2_quant_builder_generates_core6_and_supporting_states():
    result = build_case2_quant(
        quant_input(
            (
                annual_period(2023, revenue=40, gross_profit=15),
                annual_period(2024, revenue=65, gross_profit=28, shares=98),
                annual_period(
                    2025,
                    revenue=100,
                    gross_profit=45,
                    cfo=5,
                    growth_capex=2,
                    shares=100,
                ),
            )
        )
    )

    assert result.eligibility == EligibilityState.ELIGIBLE
    assert result.snapshot.state == ResolutionState.RESOLVED
    assert len([metric for metric in result.snapshot.metrics if metric.is_core]) == 6
    assert sum(metric.weight for metric in result.snapshot.metrics) == pytest.approx(1.0)
    assert result.snapshot.uncapped_grade is not None
    assert result.snapshot.grade is not None
    assert result.snapshot.growth_scope == GrowthScope.SAME_SCOPE
    assert next(
        metric for metric in result.snapshot.metrics if metric.name == "potential_dilution"
    ).value == 0.12


def test_case2_quant_positive_fcf_makes_burn_and_runway_a():
    snapshot = build_case2_quant(
        quant_input(
            (
                annual_period(2023, revenue=50, gross_profit=20),
                annual_period(2024, revenue=70, gross_profit=30),
                annual_period(
                    2025,
                    revenue=100,
                    gross_profit=45,
                    cfo=20,
                    growth_capex=5,
                    liquidity=None,
                ),
            )
        )
    ).snapshot
    metrics = {metric.name: metric for metric in snapshot.metrics}
    assert metrics["cash_burn_trend"].grade == Grade.A
    assert metrics["runway"].grade == Grade.A
    assert metrics["runway"].value == float("inf")


def test_case2_quant_mandatory_missing_is_unresolved_not_zero():
    snapshot = build_case2_quant(
        quant_input(
            (
                annual_period(2023, revenue=50, gross_profit=20),
                annual_period(2024, revenue=70, gross_profit=30),
                annual_period(2025, revenue=None, gross_profit=45),
            )
        )
    ).snapshot
    revenue = next(metric for metric in snapshot.metrics if metric.name == "revenue_growth")
    assert snapshot.state == ResolutionState.UNRESOLVED
    assert snapshot.score is None
    assert revenue.state == ResolutionState.UNRESOLVED
    assert revenue.value is None


def test_case2_quant_ipo_share_comparison_is_provisional_and_reweighted():
    snapshot = build_case2_quant(
        quant_input(
            (
                annual_period(2023, revenue=40, gross_profit=15),
                annual_period(2024, revenue=60, gross_profit=25),
                annual_period(2025, revenue=100, gross_profit=45),
            ),
            share_comparison_valid=False,
            growth_scope=GrowthScope.PRO_FORMA_COMPARABLE,
        )
    ).snapshot
    metrics = {metric.name: metric for metric in snapshot.metrics}
    assert snapshot.state == ResolutionState.RESOLVED
    assert snapshot.provisional is True
    assert snapshot.coverage == pytest.approx(0.75)
    assert metrics["dilution"].state == ResolutionState.UNRESOLVED
    assert metrics["revenue_per_share_growth"].state == ResolutionState.UNRESOLVED
    assert snapshot.growth_scope == GrowthScope.PRO_FORMA_COMPARABLE


def test_case2_quant_funding_stress_guardrail_preserves_uncapped_grade():
    snapshot = build_case2_quant(
        quant_input(
            (
                annual_period(2023, revenue=40, gross_profit=15),
                annual_period(
                    2024,
                    revenue=60,
                    gross_profit=28,
                    cfo=-5,
                    growth_capex=5,
                    shares=100,
                ),
                annual_period(
                    2025,
                    revenue=100,
                    gross_profit=50,
                    cfo=-15,
                    growth_capex=5,
                    liquidity=100,
                    shares=130,
                ),
            )
        )
    ).snapshot
    assert snapshot.uncapped_grade == Grade.C
    assert snapshot.grade == Grade.D
    assert snapshot.grade_caps[0].trigger == "cash_burn_x_and_dilution_x"


@pytest.mark.parametrize(
    ("growth", "expected"),
    [
        (0.25, DirectionState.POSITIVE),
        (0.249999, DirectionState.NEUTRAL),
        (0.10, DirectionState.NEUTRAL),
        (0.099999, DirectionState.NEGATIVE),
    ],
)
def test_current_revenue_exact_boundaries(growth, expected):
    assert momentum_signal(growth) == expected


def test_current_acceleration_exact_plus_minus_ten_points():
    assert growth_acceleration(0.30, 0.20) == AccelerationState.ACCELERATING
    assert growth_acceleration(0.10, 0.20) == AccelerationState.DECELERATING


@pytest.mark.parametrize(
    ("current_fcf", "prior_fcf", "expected"),
    [
        (-80, -100, DirectionState.POSITIVE),
        (-120, -100, DirectionState.NEUTRAL),
        (-120.001, -100, DirectionState.NEGATIVE),
    ],
)
def test_current_cash_burn_exact_twenty_percent_boundaries(
    current_fcf, prior_fcf, expected
):
    assert cash_burn_momentum(current_fcf, prior_fcf) == expected


@pytest.mark.parametrize(
    ("growth", "expected"),
    [
        (0.25, DirectionState.POSITIVE),
        (0.10, DirectionState.NEUTRAL),
        (0.099999, DirectionState.NEGATIVE),
    ],
)
def test_current_gross_profit_boundaries(growth, expected):
    result = gross_profit_momentum(
        current_gross_profit=100 * (1 + growth),
        prior_comparable_gross_profit=100,
        yoy_growth=growth,
    )
    assert result.signal == expected


def test_current_funding_exact_boundaries():
    assert funding_runway_signal(24, 0.05) == DirectionState.POSITIVE
    assert funding_runway_signal(12, 0.15) == DirectionState.NEUTRAL
    assert funding_runway_signal(11.999, 0.15) == DirectionState.NEGATIVE


def test_thesis_kpi_positive_negative_tie_unresolved_and_breaker():
    assert thesis_kpi_momentum(
        (DirectionState.POSITIVE, DirectionState.POSITIVE, DirectionState.NEGATIVE),
        thesis_breaker_triggered=False,
    ) == DirectionState.POSITIVE
    assert thesis_kpi_momentum(
        (DirectionState.NEGATIVE, DirectionState.NEGATIVE, DirectionState.POSITIVE),
        thesis_breaker_triggered=False,
    ) == DirectionState.NEGATIVE
    assert thesis_kpi_momentum(
        (DirectionState.POSITIVE, DirectionState.NEGATIVE),
        thesis_breaker_triggered=False,
    ) == DirectionState.NEUTRAL
    assert thesis_kpi_momentum(
        (DirectionState.POSITIVE, DirectionState.UNRESOLVED),
        thesis_breaker_triggered=False,
    ) == DirectionState.UNRESOLVED
    assert thesis_kpi_momentum(
        (DirectionState.POSITIVE, DirectionState.POSITIVE),
        thesis_breaker_triggered=True,
    ) == DirectionState.NEGATIVE


def current_input(**updates) -> Case2CurrentInput:
    values = dict(
        snapshot_id="current-synthetic",
        ticker="SYNTH",
        period_end=date(2026, 6, 30),
        available_at=datetime(2026, 8, 1, tzinfo=UTC),
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        growth_scope=GrowthScope.SAME_SCOPE,
        annual_quant_grade=Grade.D,
        annual_revenue_growth=0.20,
        current_revenue=150,
        prior_comparable_revenue=100,
        current_gross_profit=70,
        prior_comparable_gross_profit=40,
        current_cfo=-5,
        current_growth_capex=5,
        prior_comparable_cfo=-15,
        prior_comparable_growth_capex=5,
        current_runway_months=30,
        actual_shares_growth=0.03,
        primary_kpi_states=(DirectionState.POSITIVE, DirectionState.POSITIVE),
    )
    values.update(updates)
    return Case2CurrentInput(**values)


def test_current_engine_derives_inflection_and_preserves_annual_quant_reference():
    snapshot = build_case2_current_trend(current_input())
    assert snapshot.overall == DirectionState.STRONG_POSITIVE
    assert TrendFlag.COMMERCIAL_INFLECTION in snapshot.flags
    assert snapshot.annual_quant_grade_reference == Grade.D
    assert snapshot.growth_scope == GrowthScope.SAME_SCOPE


def test_current_engine_derives_commercial_deterioration_and_funding_stress():
    snapshot = build_case2_current_trend(
        current_input(
            annual_quant_grade=Grade.A,
            current_revenue=105,
            current_gross_profit=39,
            current_cfo=-35,
            current_growth_capex=5,
            actual_shares_growth=0.25,
            current_runway_months=5,
            primary_kpi_states=(DirectionState.NEGATIVE, DirectionState.NEGATIVE),
        )
    )
    assert TrendFlag.COMMERCIAL_DETERIORATION in snapshot.flags
    assert TrendFlag.FUNDING_STRESS in snapshot.flags
    assert snapshot.overall == DirectionState.NEGATIVE


def narrative_snapshot(states: dict[str, NarrativeState]) -> NarrativeSnapshot:
    dimensions = (
        "differentiation",
        "defensibility",
        "adoption",
        "penetration_expansion",
        "durability",
        "failure_mode",
    )
    return NarrativeSnapshot(
        snapshot_id="narrative-synthetic",
        ticker="SYNTH",
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-narrative-v1-frozen",
        thesis_id="synth-thesis",
        thesis_version=1,
        kpi_set_version=1,
        kpi_definition_ids=("kpi-1", "kpi-2"),
        assessments=tuple(
            NarrativeAssessment(
                dimension=dimension,
                state=states.get(dimension, NarrativeState.EMERGING),
            )
            for dimension in dimensions
        ),
        overall=NarrativeState.EMERGING,
        period_end=date(2025, 12, 31),
        available_at=AVAILABLE,
        as_of=AS_OF,
    )


@pytest.mark.parametrize(
    ("states", "commercial", "damaged", "expected"),
    [
        (
            dict(
                differentiation=NarrativeState.STRONG,
                adoption=NarrativeState.PROVEN,
                durability=NarrativeState.STRONG,
            ),
            True,
            False,
            NarrativeGate.CONFIRMED,
        ),
        (
            dict(
                defensibility=NarrativeState.STRONG,
                adoption=NarrativeState.STRONG,
                durability=NarrativeState.EMERGING,
            ),
            True,
            False,
            NarrativeGate.QUALIFIED,
        ),
        ({}, True, False, NarrativeGate.DEVELOPING),
        ({"adoption": NarrativeState.WEAK}, True, False, NarrativeGate.WEAK),
        ({}, True, True, NarrativeGate.WEAK),
    ],
)
def test_narrative_engine_all_nonbroken_gates(states, commercial, damaged, expected):
    result = derive_gate_from_snapshot(
        narrative_snapshot(states),
        commercial_evidence_exists=commercial,
        thesis_breaker_triggered=False,
        core_evidence_damaged=damaged,
    )
    assert result.gate == expected


def test_narrative_broken_has_precedence():
    result = derive_gate_from_snapshot(
        narrative_snapshot({"adoption": NarrativeState.WEAK}),
        commercial_evidence_exists=True,
        thesis_breaker_triggered=True,
        core_evidence_damaged=True,
    )
    assert result.gate == NarrativeGate.BROKEN
