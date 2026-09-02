"""Thin Case 2 analysis orchestration; financial formulas stay in component engines."""

from __future__ import annotations

from datetime import date, datetime

from engine.case2_current import Case2CurrentInput, build_case2_current_trend
from engine.case2_quant import Case2QuantInput, build_case2_quant
from engine.investment_grade_engine import build_investment_grade
from engine.narrative_engine import derive_gate_from_snapshot
from engine.tracking_models import (
    AnalysisCase,
    AnalysisSnapshot,
    AsymmetryType,
    FrozenDomainModel,
    NarrativeSnapshot,
    ValuationAssumptionSet,
)
from engine.valuation_engine import (
    ValuationEvidenceState,
    ValuationIdentity,
    build_case2_valuation,
)


class Case2AnalysisInput(FrozenDomainModel):
    snapshot_id: str
    investment_grade_snapshot_id: str
    company_name: str
    period_end: date
    available_at: datetime
    as_of: datetime
    quant: Case2QuantInput
    narrative: NarrativeSnapshot
    commercial_evidence_exists: bool
    thesis_breaker_triggered: bool
    core_narrative_evidence_damaged: bool = False
    current: Case2CurrentInput
    valuation_assumptions: ValuationAssumptionSet
    current_market_cap: float
    current_revenue: float
    required_return: float
    valuation_evidence: ValuationEvidenceState
    asymmetry_type: AsymmetryType


def build_case2_analysis(inputs: Case2AnalysisInput) -> AnalysisSnapshot:
    tickers = {inputs.quant.ticker, inputs.narrative.ticker, inputs.current.ticker}
    if tickers != {inputs.quant.ticker}:
        raise ValueError("all Case 2 analysis inputs must use the same ticker")
    quant_result = build_case2_quant(inputs.quant)
    narrative_result = derive_gate_from_snapshot(
        inputs.narrative,
        commercial_evidence_exists=inputs.commercial_evidence_exists,
        thesis_breaker_triggered=inputs.thesis_breaker_triggered,
        core_evidence_damaged=inputs.core_narrative_evidence_damaged,
    )
    current = build_case2_current_trend(
        inputs.current.model_copy(
            update={"annual_quant_grade": quant_result.snapshot.grade}
        )
    )
    valuation = build_case2_valuation(
        identity=ValuationIdentity(
            snapshot_id=f"{inputs.snapshot_id}-valuation",
            ticker=inputs.quant.ticker,
            period_end=inputs.period_end,
            available_at=inputs.available_at,
            as_of=inputs.as_of,
        ),
        assumptions=inputs.valuation_assumptions,
        current_market_cap=inputs.current_market_cap,
        current_revenue=inputs.current_revenue,
        required_return=inputs.required_return,
        evidence=inputs.valuation_evidence,
        asymmetry_type=inputs.asymmetry_type,
    )
    investment_grade = build_investment_grade(
        snapshot_id=inputs.investment_grade_snapshot_id,
        ticker=inputs.quant.ticker,
        period_end=inputs.period_end,
        available_at=inputs.available_at,
        as_of=inputs.as_of,
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        quant=quant_result.snapshot,
        current_trend=current,
        narrative_gate=narrative_result.gate,
        valuation=valuation,
        thesis_breaker_triggered=inputs.thesis_breaker_triggered,
    )
    return AnalysisSnapshot(
        snapshot_id=inputs.snapshot_id,
        ticker=inputs.quant.ticker,
        company_name=inputs.company_name,
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        case_definition_version="case2-v1-frozen",
        period_end=inputs.period_end,
        available_at=inputs.available_at,
        as_of=inputs.as_of,
        quant=quant_result.snapshot,
        current_trend=current,
        narrative=inputs.narrative,
        valuation=valuation,
        investment_grade=investment_grade,
    )
