"""Investment Grade v1.1 valuation-entry safety policy.

The frozen v1 policy remains importable for historical replay. This module changes only
the valuation-to-initial-grade decision: confidence can cap a grade but cannot create a
better grade, and unspecified combinations resolve to U instead of raising or guessing.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.tracking_models import (
    AsymmetryType,
    ExpectationGap,
    InvestmentGrade,
    ValuationConfidence,
)


VALUATION_UNRESOLVED = "VALUATION_UNRESOLVED"
VALUATION_COMBINATION_UNRESOLVED = "VALUATION_COMBINATION_UNRESOLVED"


@dataclass(frozen=True)
class InitialGradeDecision:
    grade: InvestmentGrade
    reason: str


def initial_grade_from_valuation_v1_1(
    *,
    expectation_gap: ExpectationGap,
    asymmetry_type: AsymmetryType,
    valuation_confidence: ValuationConfidence,
    meaningful_optionality: bool = False,
    highly_stage_sensitive: bool = False,
) -> InitialGradeDecision:
    if (
        expectation_gap == ExpectationGap.UNRESOLVED
        or valuation_confidence == ValuationConfidence.UNRESOLVED
    ):
        return InitialGradeDecision(InvestmentGrade.U, VALUATION_UNRESOLVED)
    if (
        expectation_gap == ExpectationGap.POSITIVE
        and asymmetry_type == AsymmetryType.FAVORABLE
    ):
        return InitialGradeDecision(
            InvestmentGrade.A,
            "POSITIVE_GAP_FAVORABLE_ASYMMETRY",
        )
    if expectation_gap == ExpectationGap.OVERLAP or (
        expectation_gap == ExpectationGap.POSITIVE
        and asymmetry_type == AsymmetryType.BALANCED
    ):
        return InitialGradeDecision(
            InvestmentGrade.B,
            "OVERLAP_OR_POSITIVE_BALANCED",
        )
    if expectation_gap == ExpectationGap.NEGATIVE and (
        meaningful_optionality or highly_stage_sensitive
    ):
        return InitialGradeDecision(
            InvestmentGrade.C,
            "NEGATIVE_GAP_WITH_EXPLICIT_C_EVIDENCE",
        )
    if (
        expectation_gap == ExpectationGap.NEGATIVE
        and asymmetry_type == AsymmetryType.UNFAVORABLE
    ):
        return InitialGradeDecision(
            InvestmentGrade.D,
            "NEGATIVE_GAP_UNFAVORABLE_ASYMMETRY",
        )
    return InitialGradeDecision(
        InvestmentGrade.U,
        VALUATION_COMBINATION_UNRESOLVED,
    )
