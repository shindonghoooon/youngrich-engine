from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from engine.case2_policy import CASE2_CORE_WEIGHTS
from engine.investment_grade_engine import build_investment_grade
from engine.investment_grade_engine_v1_1 import (
    CURRENT_UNRESOLVED_OPTIONAL,
    MANDATORY_NARRATIVE_UNRESOLVED,
    MANDATORY_QUANT_UNRESOLVED,
    MODEL_VERSION,
    build_investment_grade_v1_1,
)
from engine.investment_grade_policy import initial_grade_from_valuation
from engine.investment_grade_policy_v1_1 import (
    VALUATION_COMBINATION_UNRESOLVED,
    initial_grade_from_valuation_v1_1,
)
from engine.models import Grade
from engine.tracking_models import (
    AnalysisCase,
    AsymmetryType,
    AssumptionRange,
    CurrentTrendSignal,
    CurrentTrendSnapshot,
    DirectionState,
    ExitMultipleAssumption,
    ExitMultipleBand,
    ExitMultipleEvidenceSource,
    ExpectationGap,
    InvestmentGrade,
    MetricResult,
    NarrativeGate,
    QuantSnapshot,
    ResolutionState,
    TerminalStage,
    TrendFlag,
    ValuationAssumptionSet,
    ValuationConfidence,
    ValuationMetric,
    ValuationOutput,
    ValuationSnapshot,
)


UTC = timezone.utc
AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
PERIOD_END = date(2025, 12, 31)


def _assumptions(case: AnalysisCase) -> ValuationAssumptionSet:
    metric = (
        ValuationMetric.PE
        if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH
        else ValuationMetric.EV_REVENUE
    )
    return ValuationAssumptionSet(
        assumption_set_id=f"{case.value}-safety-test",
        version=1,
        case=case,
        horizon_years=3,
        terminal_stage=TerminalStage.GROWTH,
        terminal_stage_rationale="safety test",
        terminal_stage_confidence=ValuationConfidence.HIGH,
        primary_metric=metric,
        exit_multiples=tuple(
            ExitMultipleAssumption(
                band=band,
                metric_type=metric,
                value=value,
                evidence_type=ExitMultipleEvidenceSource.COMPANY_HISTORY,
                source_reference="synthetic safety test",
                as_of=AS_OF,
                rationale="policy-only test",
            )
            for band, value in zip(ExitMultipleBand, (5.0, 7.0, 9.0), strict=True)
        ),
        plausible_growth_range=AssumptionRange(low=0.10, high=0.20),
        expected_annual_dilution=(
            0.0
            if case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
            else None
        ),
        terminal_net_debt=(
            0.0
            if case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
            else None
        ),
    )


def _valuation(
    case: AnalysisCase,
    *,
    gap: ExpectationGap = ExpectationGap.POSITIVE,
    asymmetry: AsymmetryType = AsymmetryType.FAVORABLE,
    confidence: ValuationConfidence = ValuationConfidence.HIGH,
    resolved: bool = True,
    market_value: float = 100.0,
) -> ValuationSnapshot:
    return ValuationSnapshot(
        snapshot_id="valuation",
        ticker="SAFE",
        assumption_set=_assumptions(case),
        state=ResolutionState.RESOLVED if resolved else ResolutionState.UNRESOLVED,
        market_price=(
            market_value if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH else None
        ),
        market_cap=(
            market_value
            if case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
            else None
        ),
        output=(
            ValuationOutput(
                expectation_gap=gap,
                asymmetry_type=asymmetry,
                confidence=confidence,
            )
            if resolved
            else ValuationOutput()
        ),
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
    )


def _quant(
    case: AnalysisCase,
    *,
    resolved: bool = True,
    provisional_shareholder: bool = False,
) -> QuantSnapshot:
    if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH:
        metrics = (
            MetricResult(
                name="case1_core",
                state=(
                    ResolutionState.RESOLVED
                    if resolved
                    else ResolutionState.UNRESOLVED
                ),
                value=1.0 if resolved else None,
                grade=Grade.A if resolved else None,
                weight=1.0,
            ),
        )
        coverage = 1.0 if resolved else 0.0
    else:
        optional = {"dilution", "revenue_per_share_growth"}
        metrics = tuple(
            MetricResult(
                name=name,
                state=(
                    ResolutionState.UNRESOLVED
                    if provisional_shareholder and name in optional
                    else ResolutionState.RESOLVED
                ),
                value=(
                    None
                    if provisional_shareholder and name in optional
                    else 1.0
                ),
                grade=(
                    None
                    if provisional_shareholder and name in optional
                    else Grade.A
                ),
                weight=weight,
            )
            for name, weight in CASE2_CORE_WEIGHTS.items()
        )
        coverage = 0.75 if provisional_shareholder else 1.0
    return QuantSnapshot(
        snapshot_id="quant",
        ticker="SAFE",
        case=case,
        model_version="frozen-quant",
        metrics=metrics,
        state=ResolutionState.RESOLVED if resolved else ResolutionState.UNRESOLVED,
        score=4.0 if resolved else None,
        uncapped_grade=Grade.A if resolved else None,
        grade=Grade.A if resolved else None,
        coverage=coverage,
        provisional=provisional_shareholder,
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
    )


def _current(*, funding_stress: bool = False) -> CurrentTrendSnapshot:
    flags = frozenset({TrendFlag.FUNDING_STRESS}) if funding_stress else frozenset()
    return CurrentTrendSnapshot(
        snapshot_id="current",
        ticker="SAFE",
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-current-v1-frozen",
        signals=(CurrentTrendSignal(name="test", state=DirectionState.POSITIVE),),
        overall=DirectionState.POSITIVE,
        flags=flags,
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
    )


def _v1_1(
    case: AnalysisCase,
    *,
    quant: QuantSnapshot | None = None,
    narrative_gate: NarrativeGate | None = None,
    valuation: ValuationSnapshot | None = None,
    current: CurrentTrendSnapshot | None = None,
    breaker: bool = False,
    meaningful_optionality: bool = False,
):
    return build_investment_grade_v1_1(
        snapshot_id="ig-v1.1",
        ticker="SAFE",
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
        case=case,
        quant=quant or _quant(case),
        current_trend=current,
        narrative_gate=narrative_gate,
        valuation=valuation or _valuation(case),
        thesis_breaker_triggered=breaker,
        meaningful_optionality=meaningful_optionality,
    )


def test_v1_missing_quant_path_is_reproduced_and_v1_1_blocks_it():
    case = AnalysisCase.CASE_1_PROFITABLE_GROWTH
    unresolved = _quant(case, resolved=False)
    old = build_investment_grade(
        snapshot_id="ig-v1",
        ticker="SAFE",
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
        case=case,
        quant=unresolved,
        current_trend=None,
        narrative_gate=None,
        valuation=_valuation(case),
        thesis_breaker_triggered=False,
    )
    safe = _v1_1(case, quant=unresolved)

    assert old.final_grade == InvestmentGrade.A
    assert safe.final_grade == InvestmentGrade.U
    assert safe.adjustments[0].reason == MANDATORY_QUANT_UNRESOLVED


@pytest.mark.parametrize("gate", (None, NarrativeGate.UNRESOLVED))
def test_case2_missing_or_unresolved_narrative_is_u(gate):
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
    old = build_investment_grade(
        snapshot_id="ig-v1",
        ticker="SAFE",
        period_end=PERIOD_END,
        available_at=AS_OF,
        as_of=AS_OF,
        case=case,
        quant=_quant(case),
        current_trend=None,
        narrative_gate=gate,
        valuation=_valuation(case),
        thesis_breaker_triggered=False,
    )
    result = _v1_1(
        case,
        narrative_gate=gate,
    )
    assert old.final_grade == InvestmentGrade.A
    assert result.final_grade == InvestmentGrade.U
    assert result.adjustments[0].reason == MANDATORY_NARRATIVE_UNRESOLVED


def test_case1_missing_narrative_and_optional_current_do_not_force_u():
    result = _v1_1(AnalysisCase.CASE_1_PROFITABLE_GROWTH)
    assert result.final_grade == InvestmentGrade.A
    assert any(
        item.reason == CURRENT_UNRESOLVED_OPTIONAL for item in result.adjustments
    )


def test_case2_approved_provisional_shareholder_quant_remains_usable():
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
    result = _v1_1(
        case,
        quant=_quant(case, provisional_shareholder=True),
        narrative_gate=NarrativeGate.CONFIRMED,
    )
    assert result.final_grade == InvestmentGrade.A
    assert result.model_version == MODEL_VERSION


def test_breaker_precedes_missing_mandatory_inputs():
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
    result = _v1_1(
        case,
        quant=_quant(case, resolved=False),
        narrative_gate=None,
        valuation=_valuation(case, resolved=False),
        breaker=True,
    )
    assert result.final_grade == InvestmentGrade.X
    assert result.thesis_breaker_active is True


def test_low_confidence_no_longer_creates_negative_gap_c_upgrade():
    with pytest.raises(ValueError, match="not specified"):
        initial_grade_from_valuation(
            expectation_gap=ExpectationGap.NEGATIVE,
            asymmetry_type=AsymmetryType.BINARY,
            valuation_confidence=ValuationConfidence.HIGH,
        )
    assert initial_grade_from_valuation(
        expectation_gap=ExpectationGap.NEGATIVE,
        asymmetry_type=AsymmetryType.BINARY,
        valuation_confidence=ValuationConfidence.LOW,
    ) == InvestmentGrade.C

    for confidence in (ValuationConfidence.HIGH, ValuationConfidence.LOW):
        decision = initial_grade_from_valuation_v1_1(
            expectation_gap=ExpectationGap.NEGATIVE,
            asymmetry_type=AsymmetryType.BINARY,
            valuation_confidence=confidence,
        )
        assert decision.grade == InvestmentGrade.U
        assert decision.reason == VALUATION_COMBINATION_UNRESOLVED


@pytest.mark.parametrize("confidence", (ValuationConfidence.HIGH, ValuationConfidence.LOW))
def test_negative_unfavorable_is_d_regardless_of_confidence(confidence):
    case = AnalysisCase.CASE_1_PROFITABLE_GROWTH
    result = _v1_1(
        case,
        valuation=_valuation(
            case,
            gap=ExpectationGap.NEGATIVE,
            asymmetry=AsymmetryType.UNFAVORABLE,
            confidence=confidence,
        ),
    )
    assert result.final_grade == InvestmentGrade.D


@pytest.mark.parametrize("confidence", (ValuationConfidence.HIGH, ValuationConfidence.LOW))
def test_negative_binary_requires_explicit_c_evidence(confidence):
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
    valuation = _valuation(
        case,
        gap=ExpectationGap.NEGATIVE,
        asymmetry=AsymmetryType.BINARY,
        confidence=confidence,
    )
    unresolved = _v1_1(
        case,
        narrative_gate=NarrativeGate.CONFIRMED,
        valuation=valuation,
    )
    supported = _v1_1(
        case,
        narrative_gate=NarrativeGate.CONFIRMED,
        valuation=valuation,
        meaningful_optionality=True,
    )
    assert unresolved.final_grade == InvestmentGrade.U
    assert unresolved.adjustments[0].reason == VALUATION_COMBINATION_UNRESOLVED
    assert supported.final_grade == InvestmentGrade.C
    assert supported.rationale == "NEGATIVE_GAP_WITH_EXPLICIT_C_EVIDENCE"


def test_positive_favorable_low_confidence_only_caps_downward():
    case = AnalysisCase.CASE_1_PROFITABLE_GROWTH
    high = _v1_1(case, valuation=_valuation(case, confidence=ValuationConfidence.HIGH))
    low = _v1_1(case, valuation=_valuation(case, confidence=ValuationConfidence.LOW))
    assert high.final_grade == InvestmentGrade.A
    assert low.initial_valuation_grade == InvestmentGrade.A
    assert low.final_grade == InvestmentGrade.B


def test_funding_stress_cap_survives_price_only_change():
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
    results = [
        _v1_1(
            case,
            narrative_gate=NarrativeGate.CONFIRMED,
            current=_current(funding_stress=True),
            valuation=_valuation(case, market_value=market_value),
        )
        for market_value in (1_000.0, 400.0)
    ]
    assert [item.final_grade for item in results] == [InvestmentGrade.C, InvestmentGrade.C]
