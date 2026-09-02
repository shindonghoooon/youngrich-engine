"""Deterministic Investment Grade v1 composition from upstream snapshots."""

from __future__ import annotations

from datetime import date, datetime

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
from engine.tracking_models import (
    AdjustmentType,
    AnalysisCase,
    CurrentTrendSnapshot,
    InvestmentGrade,
    InvestmentGradeAdjustment,
    InvestmentGradeSnapshot,
    InvestmentGradeTrigger,
    NarrativeGate,
    QuantSnapshot,
    ResolutionState,
    TrendFlag,
    ValuationSnapshot,
)


def build_investment_grade(
    *,
    snapshot_id: str,
    ticker: str,
    period_end: date,
    available_at: datetime,
    as_of: datetime,
    case: AnalysisCase,
    quant: QuantSnapshot,
    current_trend: CurrentTrendSnapshot | None,
    narrative_gate: NarrativeGate | None,
    valuation: ValuationSnapshot,
    thesis_breaker_triggered: bool,
) -> InvestmentGradeSnapshot:
    broken_narrative = narrative_gate == NarrativeGate.BROKEN
    valuation_unresolved = (
        valuation.state == ResolutionState.UNRESOLVED
        or valuation.output.expectation_gap.value == "unresolved"
        or valuation.output.confidence.value == "unresolved"
    )
    if thesis_breaker_triggered or broken_narrative:
        trigger = (
            InvestmentGradeTrigger.THESIS_BREAKER
            if thesis_breaker_triggered
            else InvestmentGradeTrigger.NARRATIVE
        )
        adjustment = InvestmentGradeAdjustment(
            sequence=1,
            adjustment_type=AdjustmentType.GATE,
            trigger=trigger,
            active=True,
            maximum_grade=InvestmentGrade.X,
            reason="global Thesis Breaker/Narrative BROKEN precedence",
        )
        if valuation_unresolved:
            initial = InvestmentGrade.U
        else:
            try:
                initial = initial_grade_from_valuation(
                    expectation_gap=valuation.output.expectation_gap,
                    asymmetry_type=valuation.output.asymmetry_type,
                    valuation_confidence=valuation.output.confidence,
                )
            except ValueError:
                initial = InvestmentGrade.U
        return InvestmentGradeSnapshot(
            snapshot_id=snapshot_id,
            ticker=ticker,
            model_version="investment-grade-v1-frozen",
            period_end=period_end,
            available_at=available_at,
            as_of=as_of,
            initial_valuation_grade=initial,
            final_grade=InvestmentGrade.X,
            adjustments=(adjustment,),
            thesis_breaker_active=thesis_breaker_triggered,
        )
    if valuation_unresolved:
        adjustment = InvestmentGradeAdjustment(
            sequence=1,
            adjustment_type=AdjustmentType.GATE,
            trigger=InvestmentGradeTrigger.VALUATION_CONFIDENCE,
            active=True,
            maximum_grade=InvestmentGrade.U,
            reason="valuation unresolved global precedence",
        )
        return InvestmentGradeSnapshot(
            snapshot_id=snapshot_id,
            ticker=ticker,
            model_version="investment-grade-v1-frozen",
            period_end=period_end,
            available_at=available_at,
            as_of=as_of,
            initial_valuation_grade=InvestmentGrade.U,
            final_grade=InvestmentGrade.U,
            adjustments=(adjustment,),
        )

    initial = initial_grade_from_valuation(
        expectation_gap=valuation.output.expectation_gap,
        asymmetry_type=valuation.output.asymmetry_type,
        valuation_confidence=valuation.output.confidence,
    )
    adjustments: list[InvestmentGradeAdjustment] = []

    def add_cap(trigger: InvestmentGradeTrigger, cap: InvestmentGrade | None, reason: str) -> None:
        if cap is not None:
            adjustments.append(
                InvestmentGradeAdjustment(
                    sequence=len(adjustments) + 1,
                    adjustment_type=AdjustmentType.CAP,
                    trigger=trigger,
                    active=True,
                    maximum_grade=cap,
                    reason=reason,
                )
            )

    if (
        case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
        and narrative_gate
    ):
        add_cap(
            InvestmentGradeTrigger.NARRATIVE,
            narrative_gate_cap(narrative_gate),
            "Case 2 Narrative gate cap",
        )
    if quant.grade is not None:
        if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH:
            add_cap(InvestmentGradeTrigger.QUANT, case1_quant_cap(quant.grade), "Case 1 Quant cap")
        else:
            inflection = bool(
                current_trend
                and TrendFlag.COMMERCIAL_INFLECTION in current_trend.flags
            )
            add_cap(
                InvestmentGradeTrigger.QUANT,
                case2_quant_cap(
                    quant.grade,
                    commercial_inflection=inflection,
                    narrative_gate=narrative_gate or NarrativeGate.UNRESOLVED,
                ),
                "Case 2 Quant cap",
            )
    if current_trend is not None:
        deterioration = TrendFlag.COMMERCIAL_DETERIORATION in current_trend.flags
        add_cap(
            InvestmentGradeTrigger.CURRENT_TREND,
            current_trend_cap(current_trend.overall),
            "Current Trend cap",
        )
        add_cap(
            InvestmentGradeTrigger.COMMERCIAL_DETERIORATION,
            InvestmentGrade.D if deterioration else None,
            "Commercial Deterioration cap",
        )
        if case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH:
            add_cap(
                InvestmentGradeTrigger.FUNDING_STRESS,
                funding_stress_cap(TrendFlag.FUNDING_STRESS in current_trend.flags),
                "Funding Stress cap",
            )
    add_cap(
        InvestmentGradeTrigger.VALUATION_CONFIDENCE,
        valuation_confidence_cap(valuation.output.confidence),
        "Valuation Confidence cap",
    )
    final = apply_grade_adjustments(initial, tuple(adjustments))
    return InvestmentGradeSnapshot(
        snapshot_id=snapshot_id,
        ticker=ticker,
        model_version="investment-grade-v1-frozen",
        period_end=period_end,
        available_at=available_at,
        as_of=as_of,
        initial_valuation_grade=initial,
        final_grade=final,
        adjustments=tuple(adjustments),
        thesis_breaker_active=False,
    )
