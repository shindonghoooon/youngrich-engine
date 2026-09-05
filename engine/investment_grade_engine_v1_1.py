"""Decision-safe Investment Grade v1.1 composition.

Frozen v1 remains in ``investment_grade_engine.py`` for exact historical replay. v1.1
adds mandatory-evidence gates and removes confidence-only initial-grade improvement while
reusing the frozen v1 cap ordering and thresholds.
"""

from __future__ import annotations

from datetime import date, datetime

from engine.case1_snapshot import validate_case1_core_metrics
from engine.case2_quant import validate_case2_quant_snapshot
from engine.case2_policy import (
    CASE2_MANDATORY_METRICS,
    CASE2_SHAREHOLDER_OPTIONAL_METRICS,
)
from engine.investment_grade_policy import (
    apply_grade_adjustments,
    case1_quant_cap,
    case2_quant_cap,
    current_trend_cap,
    funding_stress_cap,
    narrative_gate_cap,
    valuation_confidence_cap,
)
from engine.investment_grade_policy_v1_1 import (
    VALUATION_COMBINATION_UNRESOLVED,
    initial_grade_from_valuation_v1_1,
)
from engine.tracking_models import (
    AdjustmentType,
    AnalysisCase,
    CurrentTrendSnapshot,
    DirectionState,
    InvestmentGrade,
    InvestmentGradeAdjustment,
    InvestmentGradeSnapshot,
    InvestmentGradeTrigger,
    NarrativeGate,
    QuantSnapshot,
    ResolutionState,
    TrendFlag,
    ValuationSnapshot,
    validate_valuation_evidence_timing,
)


MODEL_VERSION = "investment-grade-v1.1-safety"
MANDATORY_QUANT_UNRESOLVED = "MANDATORY_QUANT_UNRESOLVED"
MANDATORY_QUANT_METRICS_MISSING = "MANDATORY_QUANT_METRICS_MISSING"
MANDATORY_NARRATIVE_UNRESOLVED = "MANDATORY_NARRATIVE_UNRESOLVED"
VALUATION_UNRESOLVED = "VALUATION_UNRESOLVED"
VALUATION_EVIDENCE_UNRESOLVED = "VALUATION_EVIDENCE_UNRESOLVED"
CURRENT_UNRESOLVED_OPTIONAL = "CURRENT_UNRESOLVED_OPTIONAL"

_SUPPORTED_QUANT_MODELS = {
    AnalysisCase.CASE_1_PROFITABLE_GROWTH: "case1-quant-v1-frozen",
    AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH: "case2-quant-v1-frozen",
}


def _validate_quant_contract(
    case: AnalysisCase,
    quant: QuantSnapshot,
) -> tuple[str, ...]:
    """Return genuinely missing metrics; reject malformed policy inputs.

    Missing mandatory evidence is a decision-safe ``U`` condition. A wrong Case,
    unsupported policy version, changed weight, fake Core metric, supporting disguise,
    or internally contradictory metric is invalid input and must not produce a grade.
    """
    if quant.case != case:
        raise ValueError("QuantSnapshot case must match Investment Grade case")
    expected_model = _SUPPORTED_QUANT_MODELS[case]
    if quant.model_version != expected_model:
        raise ValueError(
            f"unsupported Quant model_version for {case.value}: {quant.model_version}"
        )
    if quant.state == ResolutionState.UNRESOLVED:
        if quant.score is not None or quant.uncapped_grade is not None or quant.grade is not None:
            raise ValueError("unresolved QuantSnapshot cannot carry score or grade")
    elif quant.score is None or quant.grade is None:
        raise ValueError("resolved QuantSnapshot requires score and grade")
    if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH:
        return validate_case1_core_metrics(quant.metrics, allow_missing=True)
    return validate_case2_quant_snapshot(quant, allow_missing=True)


def _adjustment(
    *,
    sequence: int,
    trigger: InvestmentGradeTrigger,
    reason: str,
    maximum_grade: InvestmentGrade | None = None,
    gate: bool = False,
) -> InvestmentGradeAdjustment:
    return InvestmentGradeAdjustment(
        sequence=sequence,
        adjustment_type=AdjustmentType.GATE if gate else AdjustmentType.CAP,
        trigger=trigger,
        active=True,
        maximum_grade=maximum_grade,
        reason=reason,
    )


def _snapshot(
    *,
    snapshot_id: str,
    ticker: str,
    period_end: date,
    available_at: datetime,
    as_of: datetime,
    initial: InvestmentGrade,
    final: InvestmentGrade,
    adjustments: tuple[InvestmentGradeAdjustment, ...],
    thesis_breaker_active: bool = False,
    rationale: str | None = None,
) -> InvestmentGradeSnapshot:
    return InvestmentGradeSnapshot(
        snapshot_id=snapshot_id,
        ticker=ticker,
        model_version=MODEL_VERSION,
        period_end=period_end,
        available_at=available_at,
        as_of=as_of,
        initial_valuation_grade=initial,
        final_grade=final,
        adjustments=adjustments,
        thesis_breaker_active=thesis_breaker_active,
        rationale=rationale,
    )


def _mandatory_quant_resolved(
    case: AnalysisCase,
    quant: QuantSnapshot,
) -> bool:
    if quant.state != ResolutionState.RESOLVED or quant.grade is None:
        return False
    unresolved_core = {
        metric.name
        for metric in quant.metrics
        if metric.is_core and metric.state == ResolutionState.UNRESOLVED
    }
    if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH:
        return not unresolved_core
    return not (unresolved_core & CASE2_MANDATORY_METRICS) and unresolved_core.issubset(
        CASE2_SHAREHOLDER_OPTIONAL_METRICS
    )


def build_investment_grade_v1_1(
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
    meaningful_optionality: bool = False,
    highly_stage_sensitive: bool = False,
) -> InvestmentGradeSnapshot:
    missing_quant_metrics = _validate_quant_contract(case, quant)
    if valuation.assumption_set.case != case:
        raise ValueError("Valuation assumption Case must match Investment Grade case")
    validate_valuation_evidence_timing(
        evaluation_as_of=as_of,
        assumption_set=valuation.assumption_set,
        evidence_available_at=valuation.evidence_available_at,
        evidence_retrieved_at=valuation.evidence_retrieved_at,
    )
    broken_narrative = narrative_gate == NarrativeGate.BROKEN
    valuation_unresolved = (
        valuation.state == ResolutionState.UNRESOLVED
        or valuation.output.expectation_gap.value == "unresolved"
        or valuation.output.confidence.value == "unresolved"
    )

    # A valid terminal breaker remains stronger than missing evidence.
    if thesis_breaker_triggered or broken_narrative:
        trigger = (
            InvestmentGradeTrigger.THESIS_BREAKER
            if thesis_breaker_triggered
            else InvestmentGradeTrigger.NARRATIVE
        )
        decision = initial_grade_from_valuation_v1_1(
            expectation_gap=valuation.output.expectation_gap,
            asymmetry_type=valuation.output.asymmetry_type,
            valuation_confidence=valuation.output.confidence,
            meaningful_optionality=meaningful_optionality,
            highly_stage_sensitive=highly_stage_sensitive,
        )
        return _snapshot(
            snapshot_id=snapshot_id,
            ticker=ticker,
            period_end=period_end,
            available_at=available_at,
            as_of=as_of,
            initial=decision.grade,
            final=InvestmentGrade.X,
            adjustments=(
                _adjustment(
                    sequence=1,
                    trigger=trigger,
                    maximum_grade=InvestmentGrade.X,
                    reason="THESIS_BREAKER_OR_NARRATIVE_BROKEN",
                    gate=True,
                ),
            ),
            thesis_breaker_active=thesis_breaker_triggered,
            rationale="THESIS_BREAKER_OR_NARRATIVE_BROKEN",
        )

    if missing_quant_metrics or not _mandatory_quant_resolved(case, quant):
        quant_reason = (
            f"{MANDATORY_QUANT_METRICS_MISSING}:"
            + ",".join(missing_quant_metrics)
            if missing_quant_metrics
            else MANDATORY_QUANT_UNRESOLVED
        )
        return _snapshot(
            snapshot_id=snapshot_id,
            ticker=ticker,
            period_end=period_end,
            available_at=available_at,
            as_of=as_of,
            initial=InvestmentGrade.U,
            final=InvestmentGrade.U,
            adjustments=(
                _adjustment(
                    sequence=1,
                    trigger=InvestmentGradeTrigger.QUANT,
                    maximum_grade=InvestmentGrade.U,
                    reason=quant_reason,
                    gate=True,
                ),
            ),
            rationale=quant_reason,
        )

    if (
        case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
        and narrative_gate in {None, NarrativeGate.UNRESOLVED}
    ):
        return _snapshot(
            snapshot_id=snapshot_id,
            ticker=ticker,
            period_end=period_end,
            available_at=available_at,
            as_of=as_of,
            initial=InvestmentGrade.U,
            final=InvestmentGrade.U,
            adjustments=(
                _adjustment(
                    sequence=1,
                    trigger=InvestmentGradeTrigger.NARRATIVE,
                    maximum_grade=InvestmentGrade.U,
                    reason=MANDATORY_NARRATIVE_UNRESOLVED,
                    gate=True,
                ),
            ),
            rationale=MANDATORY_NARRATIVE_UNRESOLVED,
        )

    if valuation.evidence_available_at is None:
        return _snapshot(
            snapshot_id=snapshot_id,
            ticker=ticker,
            period_end=period_end,
            available_at=available_at,
            as_of=as_of,
            initial=InvestmentGrade.U,
            final=InvestmentGrade.U,
            adjustments=(
                _adjustment(
                    sequence=1,
                    trigger=InvestmentGradeTrigger.VALUATION_CONFIDENCE,
                    maximum_grade=InvestmentGrade.U,
                    reason=VALUATION_EVIDENCE_UNRESOLVED,
                    gate=True,
                ),
            ),
            rationale=VALUATION_EVIDENCE_UNRESOLVED,
        )

    if valuation_unresolved:
        return _snapshot(
            snapshot_id=snapshot_id,
            ticker=ticker,
            period_end=period_end,
            available_at=available_at,
            as_of=as_of,
            initial=InvestmentGrade.U,
            final=InvestmentGrade.U,
            adjustments=(
                _adjustment(
                    sequence=1,
                    trigger=InvestmentGradeTrigger.VALUATION_CONFIDENCE,
                    maximum_grade=InvestmentGrade.U,
                    reason=VALUATION_UNRESOLVED,
                    gate=True,
                ),
            ),
            rationale=VALUATION_UNRESOLVED,
        )

    decision = initial_grade_from_valuation_v1_1(
        expectation_gap=valuation.output.expectation_gap,
        asymmetry_type=valuation.output.asymmetry_type,
        valuation_confidence=valuation.output.confidence,
        meaningful_optionality=meaningful_optionality,
        highly_stage_sensitive=highly_stage_sensitive,
    )
    if decision.grade == InvestmentGrade.U:
        return _snapshot(
            snapshot_id=snapshot_id,
            ticker=ticker,
            period_end=period_end,
            available_at=available_at,
            as_of=as_of,
            initial=InvestmentGrade.U,
            final=InvestmentGrade.U,
            adjustments=(
                _adjustment(
                    sequence=1,
                    trigger=InvestmentGradeTrigger.VALUATION_CONFIDENCE,
                    maximum_grade=InvestmentGrade.U,
                    reason=VALUATION_COMBINATION_UNRESOLVED,
                    gate=True,
                ),
            ),
            rationale=VALUATION_COMBINATION_UNRESOLVED,
        )

    adjustments: list[InvestmentGradeAdjustment] = []

    def add(
        trigger: InvestmentGradeTrigger,
        cap: InvestmentGrade | None,
        reason: str,
        *,
        observation: bool = False,
    ) -> None:
        if cap is not None or observation:
            adjustments.append(
                _adjustment(
                    sequence=len(adjustments) + 1,
                    trigger=trigger,
                    maximum_grade=cap,
                    reason=reason,
                    gate=observation,
                )
            )

    if (
        case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
        and narrative_gate is not None
    ):
        add(
            InvestmentGradeTrigger.NARRATIVE,
            narrative_gate_cap(narrative_gate),
            "Case 2 Narrative gate cap",
        )

    if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH:
        add(
            InvestmentGradeTrigger.QUANT,
            case1_quant_cap(quant.grade),
            "Case 1 Quant cap",
        )
    else:
        inflection = bool(
            current_trend
            and TrendFlag.COMMERCIAL_INFLECTION in current_trend.flags
        )
        add(
            InvestmentGradeTrigger.QUANT,
            case2_quant_cap(
                quant.grade,
                commercial_inflection=inflection,
                narrative_gate=narrative_gate or NarrativeGate.UNRESOLVED,
            ),
            "Case 2 Quant cap",
        )

    if current_trend is None or current_trend.overall == DirectionState.UNRESOLVED:
        add(
            InvestmentGradeTrigger.CURRENT_TREND,
            None,
            CURRENT_UNRESOLVED_OPTIONAL,
            observation=True,
        )
    else:
        add(
            InvestmentGradeTrigger.CURRENT_TREND,
            current_trend_cap(current_trend.overall),
            "Current Trend cap",
        )

    if current_trend is not None:
        deterioration = TrendFlag.COMMERCIAL_DETERIORATION in current_trend.flags
        add(
            InvestmentGradeTrigger.COMMERCIAL_DETERIORATION,
            InvestmentGrade.D if deterioration else None,
            "Commercial Deterioration cap",
        )
        if case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH:
            add(
                InvestmentGradeTrigger.FUNDING_STRESS,
                funding_stress_cap(
                    TrendFlag.FUNDING_STRESS in current_trend.flags
                ),
                "Funding Stress cap",
            )

    add(
        InvestmentGradeTrigger.VALUATION_CONFIDENCE,
        valuation_confidence_cap(valuation.output.confidence),
        "Valuation Confidence cap",
    )
    final = apply_grade_adjustments(decision.grade, tuple(adjustments))
    return _snapshot(
        snapshot_id=snapshot_id,
        ticker=ticker,
        period_end=period_end,
        available_at=available_at,
        as_of=as_of,
        initial=decision.grade,
        final=final,
        adjustments=tuple(adjustments),
        rationale=decision.reason,
    )
