"""Frozen Investment Grade v1 gate/cap contracts.

The policy starts from a valuation-derived grade and applies explicit adjustments in
stored sequence. It deliberately contains no weighted-average scoring.
"""

from __future__ import annotations

from collections.abc import Sequence

from engine.models import Grade
from engine.tracking_models import (
    AdjustmentType,
    AsymmetryType,
    DirectionState,
    ExpectationGap,
    InvestmentGrade,
    InvestmentGradeAdjustment,
    InvestmentGradeTrigger,
    NarrativeGate,
    ValuationConfidence,
)


CASE1_QUANT_CAPS = {
    Grade.C: InvestmentGrade.B,
    Grade.D: InvestmentGrade.C,
    Grade.X: InvestmentGrade.D,
}
CASE2_QUANT_CAPS = {Grade.C: InvestmentGrade.B, Grade.D: InvestmentGrade.C}
CURRENT_TREND_CAPS = {
    DirectionState.MIXED: InvestmentGrade.B,
    DirectionState.NEGATIVE: InvestmentGrade.C,
}
NARRATIVE_GATE_CAPS = {
    NarrativeGate.QUALIFIED: InvestmentGrade.B,
    NarrativeGate.DEVELOPING: InvestmentGrade.C,
    NarrativeGate.WEAK: InvestmentGrade.D,
    NarrativeGate.BROKEN: InvestmentGrade.X,
}
VALUATION_CONFIDENCE_CAPS = {
    ValuationConfidence.LOW: InvestmentGrade.B,
    ValuationConfidence.UNRESOLVED: InvestmentGrade.U,
}
_GRADE_ORDER = {
    InvestmentGrade.A: 0,
    InvestmentGrade.B: 1,
    InvestmentGrade.C: 2,
    InvestmentGrade.D: 3,
    InvestmentGrade.X: 4,
}


def case1_quant_cap(quant_grade: Grade) -> InvestmentGrade | None:
    return CASE1_QUANT_CAPS.get(quant_grade)


def case2_quant_cap(
    quant_grade: Grade,
    *,
    commercial_inflection: bool = False,
    narrative_gate: NarrativeGate = NarrativeGate.UNRESOLVED,
) -> InvestmentGrade | None:
    if quant_grade in CASE2_QUANT_CAPS:
        return CASE2_QUANT_CAPS[quant_grade]
    if quant_grade == Grade.X:
        if commercial_inflection and narrative_gate in {
            NarrativeGate.CONFIRMED,
            NarrativeGate.QUALIFIED,
        }:
            return InvestmentGrade.C
        return InvestmentGrade.D
    return None


def narrative_gate_cap(gate: NarrativeGate) -> InvestmentGrade | None:
    return NARRATIVE_GATE_CAPS.get(gate)


def current_trend_cap(
    signal: DirectionState,
    *,
    commercial_deterioration: bool = False,
) -> InvestmentGrade | None:
    if commercial_deterioration:
        return InvestmentGrade.D
    return CURRENT_TREND_CAPS.get(signal)


def funding_stress_cap(active: bool) -> InvestmentGrade | None:
    return InvestmentGrade.C if active else None


def valuation_confidence_cap(
    confidence: ValuationConfidence,
) -> InvestmentGrade | None:
    return VALUATION_CONFIDENCE_CAPS.get(confidence)


def initial_grade_from_valuation(
    *,
    expectation_gap: ExpectationGap,
    asymmetry_type: AsymmetryType,
    valuation_confidence: ValuationConfidence,
    meaningful_optionality: bool = False,
    highly_stage_sensitive: bool = False,
) -> InvestmentGrade:
    if (
        expectation_gap == ExpectationGap.UNRESOLVED
        or valuation_confidence == ValuationConfidence.UNRESOLVED
    ):
        return InvestmentGrade.U
    if (
        expectation_gap == ExpectationGap.POSITIVE
        and asymmetry_type == AsymmetryType.FAVORABLE
    ):
        return InvestmentGrade.A
    if expectation_gap == ExpectationGap.OVERLAP or (
        expectation_gap == ExpectationGap.POSITIVE
        and asymmetry_type == AsymmetryType.BALANCED
    ):
        return InvestmentGrade.B
    if expectation_gap == ExpectationGap.NEGATIVE and (
        meaningful_optionality
        or highly_stage_sensitive
        or valuation_confidence == ValuationConfidence.LOW
    ):
        return InvestmentGrade.C
    if (
        expectation_gap == ExpectationGap.NEGATIVE
        and asymmetry_type == AsymmetryType.UNFAVORABLE
    ):
        return InvestmentGrade.D
    raise ValueError("valuation combination is not specified by Investment Grade v1")


def _restrict_grade(
    grade: InvestmentGrade,
    maximum_grade: InvestmentGrade,
) -> InvestmentGrade:
    if grade == InvestmentGrade.U or maximum_grade == InvestmentGrade.U:
        return InvestmentGrade.U
    if _GRADE_ORDER[grade] < _GRADE_ORDER[maximum_grade]:
        return maximum_grade
    return grade


def apply_grade_adjustments(
    initial_grade: InvestmentGrade,
    adjustments: Sequence[InvestmentGradeAdjustment],
) -> InvestmentGrade:
    active = [adjustment for adjustment in adjustments if adjustment.active]
    sequences = [adjustment.sequence for adjustment in active]
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        raise ValueError("active Investment Grade adjustments must have unique sequence order")

    if any(
        adjustment.trigger == InvestmentGradeTrigger.THESIS_BREAKER
        or adjustment.maximum_grade == InvestmentGrade.X
        for adjustment in active
    ):
        return InvestmentGrade.X

    final = initial_grade
    for adjustment in active:
        if adjustment.trigger == InvestmentGradeTrigger.THESIS_BREAKER:
            final = InvestmentGrade.X
            continue
        if adjustment.maximum_grade is not None:
            final = _restrict_grade(final, adjustment.maximum_grade)
        elif adjustment.adjustment_type == AdjustmentType.CAP:
            raise ValueError("active cap requires maximum_grade")
    return final
