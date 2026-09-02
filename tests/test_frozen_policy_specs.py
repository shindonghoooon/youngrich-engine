from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from engine.case2_policy import (
    AccelerationState,
    EligibilityState,
    cash_burn_momentum,
    case2_eligibility,
    commercial_deterioration_flag,
    commercial_inflection_flag,
    derive_narrative_gate,
    evaluate_case2_quant,
    funding_stress_flag,
    grade_cash_burn_trend,
    grade_dilution,
    grade_gross_profit_growth,
    grade_revenue_growth,
    grade_revenue_per_share_growth,
    grade_runway,
    gross_profit_momentum,
    growth_acceleration,
    overall_current_signal,
    thesis_kpi_momentum,
)
from engine.investment_grade_policy import (
    apply_grade_adjustments,
    case1_quant_cap,
    case2_quant_cap,
    current_trend_cap,
    funding_stress_cap,
    initial_grade_from_valuation,
    narrative_gate_cap,
    valuation_confidence_cap,
)
from engine.models import Grade
from engine.tracking_models import (
    AdjustmentType,
    AsymmetryType,
    DirectionState,
    ExecutablePriceSnapshot,
    ExpectationGap,
    InvestmentGrade,
    InvestmentGradeAdjustment,
    InvestmentGradeTrigger,
    NarrativeGate,
    NarrativeState,
    ResolutionState,
    TerminalStage,
    ValuationConfidence,
    ValuationMetric,
    AssumptionRange,
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


def test_current_acceleration_exact_boundaries_are_directional():
    assert growth_acceleration(0.30, 0.20) == AccelerationState.ACCELERATING
    assert growth_acceleration(0.10, 0.20) == AccelerationState.DECELERATING
    assert growth_acceleration(0.299, 0.20) == AccelerationState.STABLE


def test_thesis_kpi_momentum_order_and_unresolved_exclusion():
    assert thesis_kpi_momentum(
        [DirectionState.POSITIVE, DirectionState.UNRESOLVED],
        thesis_breaker_triggered=False,
    ) == DirectionState.UNRESOLVED
    assert thesis_kpi_momentum(
        [DirectionState.POSITIVE, DirectionState.NEGATIVE],
        thesis_breaker_triggered=False,
    ) == DirectionState.NEUTRAL
    assert thesis_kpi_momentum(
        [DirectionState.POSITIVE, DirectionState.NEUTRAL, DirectionState.UNRESOLVED],
        thesis_breaker_triggered=False,
    ) == DirectionState.POSITIVE
    assert thesis_kpi_momentum(
        [DirectionState.POSITIVE, DirectionState.POSITIVE],
        thesis_breaker_triggered=True,
    ) == DirectionState.NEGATIVE


def test_expectation_gap_ranges_and_touching_boundary():
    required = AssumptionRange(low=0.20, high=0.30)
    assert expectation_gap_for_ranges(
        required=required,
        plausible=AssumptionRange(low=0.31, high=0.40),
    ) == ExpectationGap.POSITIVE
    assert expectation_gap_for_ranges(
        required=required,
        plausible=AssumptionRange(low=0.10, high=0.19),
    ) == ExpectationGap.NEGATIVE
    assert expectation_gap_for_ranges(
        required=required,
        plausible=AssumptionRange(low=0.10, high=0.20),
    ) == ExpectationGap.OVERLAP


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            dict(
                credible_evidence_count=0,
                company_economics_stable=False,
                company_economics_rapidly_changing=False,
                terminal_stage_confidence=ValuationConfidence.HIGH,
            ),
            ValuationConfidence.UNRESOLVED,
        ),
        (
            dict(
                credible_evidence_count=2,
                company_economics_stable=True,
                company_economics_rapidly_changing=False,
                terminal_stage_confidence=ValuationConfidence.HIGH,
            ),
            ValuationConfidence.HIGH,
        ),
        (
            dict(
                credible_evidence_count=2,
                company_economics_stable=False,
                company_economics_rapidly_changing=True,
                terminal_stage_confidence=ValuationConfidence.HIGH,
            ),
            ValuationConfidence.LOW,
        ),
        (
            dict(
                credible_evidence_count=2,
                company_economics_stable=False,
                company_economics_rapidly_changing=False,
                terminal_stage_confidence=ValuationConfidence.MEDIUM,
            ),
            ValuationConfidence.MEDIUM,
        ),
    ],
)
def test_valuation_confidence_priority(kwargs, expected):
    assert derive_valuation_confidence(**kwargs) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.40, Grade.A),
        (0.3999, Grade.B),
        (0.25, Grade.B),
        (0.2499, Grade.C),
        (0.15, Grade.C),
        (0.1499, Grade.D),
        (0.0, Grade.D),
        (-0.0001, Grade.X),
    ],
)
def test_case2_revenue_growth_boundaries(value, expected):
    assert grade_revenue_growth(value) == expected


def test_case2_eligibility_requires_commercial_emerging_growth_profile():
    assert case2_eligibility(
        core_business_revenue=10,
        gross_profit=4,
        operating_income=-3,
        core_revenue_representative=True,
        commercial_evidence_exists=True,
    ) == EligibilityState.ELIGIBLE
    assert case2_eligibility(
        core_business_revenue=0,
        gross_profit=0,
        operating_income=-3,
        core_revenue_representative=True,
        commercial_evidence_exists=False,
    ) == EligibilityState.INELIGIBLE
    assert case2_eligibility(
        core_business_revenue=None,
        gross_profit=4,
        operating_income=-3,
        core_revenue_representative=True,
        commercial_evidence_exists=True,
    ) == EligibilityState.UNRESOLVED


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.45, Grade.A),
        (0.4499, Grade.B),
        (0.30, Grade.B),
        (0.2999, Grade.C),
        (0.15, Grade.C),
        (0.1499, Grade.D),
        (0.0, Grade.D),
        (-0.0001, Grade.X),
    ],
)
def test_case2_gross_profit_growth_boundaries(value, expected):
    assert grade_gross_profit_growth(value) == expected


@pytest.mark.parametrize(
    ("latest_fcf", "previous_fcf", "expected"),
    [
        (1, -100, Grade.A),
        (-70, -100, Grade.A),
        (-90, -100, Grade.B),
        (-100, -100, Grade.C),
        (-110, -100, Grade.C),
        (-111, -100, Grade.D),
        (-150, -100, Grade.D),
        (-151, -100, Grade.X),
        (-1, 1, Grade.X),
    ],
)
def test_case2_cash_burn_boundaries_and_transitions(
    latest_fcf, previous_fcf, expected
):
    assert grade_cash_burn_trend(latest_fcf, previous_fcf) == expected


@pytest.mark.parametrize(
    ("months", "expected"),
    [
        (36, Grade.A),
        (35.99, Grade.B),
        (24, Grade.B),
        (23.99, Grade.C),
        (12, Grade.C),
        (11.99, Grade.D),
        (6, Grade.D),
        (5.99, Grade.X),
    ],
)
def test_case2_runway_boundaries(months, expected):
    annual_burn = 120
    liquidity = annual_burn * months / 12
    assert grade_runway(liquidity, -annual_burn) == expected


def test_fcf_positive_runway_is_a():
    assert grade_runway(None, 1) == Grade.A


@pytest.mark.parametrize(
    ("dilution", "expected"),
    [
        (0.02, Grade.A),
        (0.0201, Grade.B),
        (0.05, Grade.B),
        (0.0501, Grade.C),
        (0.10, Grade.C),
        (0.1001, Grade.D),
        (0.20, Grade.D),
        (0.2001, Grade.X),
    ],
)
def test_case2_actual_share_dilution_boundaries(dilution, expected):
    assert grade_dilution(dilution) == expected


@pytest.mark.parametrize(
    ("growth", "expected"),
    [
        (0.30, Grade.A),
        (0.2999, Grade.B),
        (0.20, Grade.B),
        (0.1999, Grade.C),
        (0.10, Grade.C),
        (0.0999, Grade.D),
        (0.0, Grade.D),
        (-0.0001, Grade.X),
    ],
)
def test_case2_revenue_per_share_boundaries(growth, expected):
    assert grade_revenue_per_share_growth(growth) == expected


def test_case2_funding_stress_guardrail_preserves_raw_score_and_caps_grade():
    result = evaluate_case2_quant(
        {
            "revenue_growth": Grade.A,
            "gross_profit_growth": Grade.A,
            "cash_burn_trend": Grade.X,
            "runway": Grade.A,
            "dilution": Grade.X,
            "revenue_per_share_growth": Grade.A,
        }
    )

    assert result.raw_score == pytest.approx(2.80)
    assert result.uncapped_grade == Grade.C
    assert result.final_grade == Grade.D
    assert result.funding_stress_cap_applied is True


def test_case2_mandatory_unresolved_makes_quant_unresolved():
    result = evaluate_case2_quant(
        {
            "revenue_growth": None,
            "gross_profit_growth": Grade.A,
            "cash_burn_trend": Grade.B,
            "runway": Grade.B,
            "dilution": Grade.A,
            "revenue_per_share_growth": Grade.A,
        }
    )

    assert result.state == ResolutionState.UNRESOLVED
    assert result.raw_score is None
    assert result.final_grade is None
    assert result.coverage == pytest.approx(0.70)


def test_case2_shareholder_unresolved_renormalizes_provisional_score():
    result = evaluate_case2_quant(
        {
            "revenue_growth": Grade.A,
            "gross_profit_growth": Grade.B,
            "cash_burn_trend": Grade.C,
            "runway": Grade.D,
            "dilution": None,
            "revenue_per_share_growth": None,
        }
    )

    expected = (4 * 0.30 + 3 * 0.15 + 2 * 0.15 + 1 * 0.15) / 0.75
    assert result.state == ResolutionState.RESOLVED
    assert result.raw_score == pytest.approx(expected)
    assert result.coverage == pytest.approx(0.75)
    assert result.provisional is True


def test_current_cash_burn_positive_negative_transitions():
    assert cash_burn_momentum(1, -100) == DirectionState.POSITIVE
    assert cash_burn_momentum(-1, 1) == DirectionState.NEGATIVE


def test_gross_profit_turning_negative_sets_warning():
    result = gross_profit_momentum(
        current_gross_profit=-1,
        prior_comparable_gross_profit=1,
        yoy_growth=None,
    )

    assert result.signal == DirectionState.NEGATIVE
    assert result.warning == "gross profit turned negative"


def test_case2_current_mixed_precedes_positive():
    signals = (
        DirectionState.POSITIVE,
        DirectionState.POSITIVE,
        DirectionState.POSITIVE,
        DirectionState.NEGATIVE,
        DirectionState.NEGATIVE,
    )
    assert overall_current_signal(signals) == DirectionState.MIXED


def test_current_funding_stress_requires_both_strict_thresholds():
    assert funding_stress_flag(0.51, 0.21) is True
    assert funding_stress_flag(0.50, 0.21) is False
    assert funding_stress_flag(0.51, 0.20) is False
    assert funding_stress_flag(None, 0.21) is None


def test_commercial_inflection_and_deterioration_flags():
    assert commercial_inflection_flag(
        Grade.D,
        DirectionState.POSITIVE,
        DirectionState.POSITIVE,
        DirectionState.POSITIVE,
    )
    assert commercial_deterioration_flag(
        Grade.A,
        DirectionState.NEGATIVE,
        DirectionState.NEGATIVE,
        DirectionState.NEGATIVE,
    )


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {
                "differentiation": NarrativeState.STRONG,
                "defensibility": NarrativeState.EMERGING,
                "adoption": NarrativeState.PROVEN,
                "durability": NarrativeState.STRONG,
                "commercial_evidence_exists": True,
                "thesis_breaker_triggered": False,
            },
            NarrativeGate.CONFIRMED,
        ),
        (
            {
                "differentiation": NarrativeState.EMERGING,
                "defensibility": NarrativeState.STRONG,
                "adoption": NarrativeState.STRONG,
                "durability": NarrativeState.EMERGING,
                "commercial_evidence_exists": True,
                "thesis_breaker_triggered": False,
            },
            NarrativeGate.QUALIFIED,
        ),
        (
            {
                "differentiation": NarrativeState.EMERGING,
                "defensibility": NarrativeState.EMERGING,
                "adoption": NarrativeState.EMERGING,
                "durability": NarrativeState.EMERGING,
                "commercial_evidence_exists": True,
                "thesis_breaker_triggered": False,
            },
            NarrativeGate.DEVELOPING,
        ),
        (
            {
                "differentiation": NarrativeState.STRONG,
                "defensibility": NarrativeState.STRONG,
                "adoption": NarrativeState.WEAK,
                "durability": NarrativeState.STRONG,
                "commercial_evidence_exists": True,
                "thesis_breaker_triggered": False,
            },
            NarrativeGate.WEAK,
        ),
        (
            {
                "differentiation": NarrativeState.PROVEN,
                "defensibility": NarrativeState.PROVEN,
                "adoption": NarrativeState.PROVEN,
                "durability": NarrativeState.PROVEN,
                "commercial_evidence_exists": True,
                "thesis_breaker_triggered": True,
            },
            NarrativeGate.BROKEN,
        ),
    ],
)
def test_narrative_gate_derivation(kwargs, expected):
    assert derive_narrative_gate(**kwargs) == expected


def test_investment_grade_caps_apply_in_stored_order():
    adjustments = (
        InvestmentGradeAdjustment(
            sequence=1,
            adjustment_type=AdjustmentType.CAP,
            trigger=InvestmentGradeTrigger.QUANT,
            active=True,
            maximum_grade=InvestmentGrade.B,
            reason="Quant C caps at B",
        ),
        InvestmentGradeAdjustment(
            sequence=2,
            adjustment_type=AdjustmentType.CAP,
            trigger=InvestmentGradeTrigger.FUNDING_STRESS,
            active=True,
            maximum_grade=InvestmentGrade.C,
            reason="Funding Stress caps at C",
        ),
        InvestmentGradeAdjustment(
            sequence=3,
            adjustment_type=AdjustmentType.GATE,
            trigger=InvestmentGradeTrigger.THESIS_BREAKER,
            active=True,
            reason="Thesis Breaker forces X",
        ),
    )

    assert apply_grade_adjustments(InvestmentGrade.A, adjustments) == InvestmentGrade.X


def test_case_specific_investment_grade_cap_contracts():
    assert case1_quant_cap(Grade.C) == InvestmentGrade.B
    assert case1_quant_cap(Grade.X) == InvestmentGrade.D
    assert case2_quant_cap(Grade.D) == InvestmentGrade.C
    assert case2_quant_cap(Grade.X) == InvestmentGrade.D
    assert case2_quant_cap(
        Grade.X,
        commercial_inflection=True,
        narrative_gate=NarrativeGate.QUALIFIED,
    ) == InvestmentGrade.C
    assert narrative_gate_cap(NarrativeGate.DEVELOPING) == InvestmentGrade.C
    assert current_trend_cap(DirectionState.NEGATIVE) == InvestmentGrade.C
    assert current_trend_cap(
        DirectionState.POSITIVE,
        commercial_deterioration=True,
    ) == InvestmentGrade.D
    assert funding_stress_cap(True) == InvestmentGrade.C
    assert valuation_confidence_cap(ValuationConfidence.LOW) == InvestmentGrade.B
    assert (
        valuation_confidence_cap(ValuationConfidence.UNRESOLVED)
        == InvestmentGrade.U
    )


def test_initial_investment_grade_is_valuation_derived():
    assert initial_grade_from_valuation(
        expectation_gap=ExpectationGap.POSITIVE,
        asymmetry_type=AsymmetryType.FAVORABLE,
        valuation_confidence=ValuationConfidence.HIGH,
    ) == InvestmentGrade.A
    assert initial_grade_from_valuation(
        expectation_gap=ExpectationGap.UNRESOLVED,
        asymmetry_type=AsymmetryType.UNRESOLVED,
        valuation_confidence=ValuationConfidence.UNRESOLVED,
    ) == InvestmentGrade.U


def test_case1_required_eps_cagr_formula():
    expected = ((100 * 1.15**3) / (5 * 20)) ** (1 / 3) - 1
    assert case1_required_eps_cagr(
        current_price=100,
        current_eps=5,
        exit_pe=20,
    ) == pytest.approx(expected)


def test_case2_required_growth_formula_chain():
    equity = case2_required_future_equity_value(
        current_market_cap=500,
        expected_annual_dilution=0.05,
    )
    ev = required_future_enterprise_value(
        required_future_equity_value=equity,
        terminal_net_debt=50,
    )
    revenue = case2_required_future_revenue(
        required_future_ev=ev,
        terminal_stage=TerminalStage.GROWTH,
        primary_metric=ValuationMetric.EV_REVENUE,
        exit_multiple=5,
    )
    growth = required_revenue_cagr(
        required_future_revenue=revenue,
        current_revenue=50,
    )

    assert equity == pytest.approx(500 * 1.15**5 * 1.05**5)
    assert ev == pytest.approx(equity + 50)
    assert revenue == pytest.approx(ev / 5)
    assert growth == pytest.approx((revenue / 50) ** (1 / 5) - 1)


def test_historical_price_lookahead_is_rejected_by_policy_contract():
    with pytest.raises(ValidationError, match="cannot precede"):
        ExecutablePriceSnapshot(
            information_available_at=datetime(2026, 2, 10, 13, tzinfo=timezone.utc),
            executable_at=datetime(2025, 12, 31, 21, tzinfo=timezone.utc),
            price=100,
            source_reference="official exchange",
        )
