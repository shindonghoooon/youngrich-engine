from datetime import date, datetime, timezone

import pytest

from engine.investment_grade_engine import build_investment_grade
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
    InvestmentGrade,
    InvestmentGradeTrigger,
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
from engine.valuation_engine import (
    ValuationEvidenceState,
    ValuationIdentity,
    build_case1_valuation,
    build_case2_valuation,
)


UTC = timezone.utc
PERIOD_END = date(2025, 12, 31)
AVAILABLE = datetime(2026, 2, 15, tzinfo=UTC)
AS_OF = datetime(2026, 4, 1, tzinfo=UTC)


def assumptions(
    case: AnalysisCase,
    *,
    metric: ValuationMetric | None = None,
    stage: TerminalStage | None = None,
    multiples: tuple[float, float, float] = (10, 15, 20),
    plausible: tuple[float, float] = (0.10, 0.30),
    confidence: ValuationConfidence = ValuationConfidence.HIGH,
    dilution: float = 0.05,
    terminal_net_debt: float = 20,
) -> ValuationAssumptionSet:
    metric = metric or (
        ValuationMetric.PE
        if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH
        else ValuationMetric.EV_REVENUE
    )
    stage = stage or (
        TerminalStage.MATURE
        if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH
        else TerminalStage.GROWTH
    )
    return ValuationAssumptionSet(
        assumption_set_id=f"{case.value}-assumptions",
        version=7,
        case=case,
        horizon_years=3 if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH else 5,
        terminal_stage=stage,
        terminal_stage_rationale="synthetic frozen-policy test",
        terminal_stage_confidence=confidence,
        primary_metric=metric,
        plausible_growth_range=AssumptionRange(low=plausible[0], high=plausible[1]),
        expected_annual_dilution=(
            dilution if case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH else None
        ),
        target_gross_margin=(0.50 if metric == ValuationMetric.EV_GROSS_PROFIT else None),
        target_operating_margin=(0.20 if metric == ValuationMetric.EV_EBIT else None),
        terminal_net_debt=(
            terminal_net_debt
            if case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
            else None
        ),
        exit_multiples=tuple(
            ExitMultipleAssumption(
                band=band,
                metric_type=metric,
                value=value,
                evidence_type=ExitMultipleEvidenceSource.COMPARABLE_COMPANIES,
                source_reference=f"synthetic-{band.value}",
                as_of=AS_OF,
                rationale="synthetic test evidence",
            )
            for band, value in zip(ExitMultipleBand, multiples, strict=True)
        ),
    )


def identity(ticker: str = "SYNTH") -> ValuationIdentity:
    return ValuationIdentity(
        snapshot_id=f"{ticker}-valuation",
        ticker=ticker,
        period_end=PERIOD_END,
        available_at=AVAILABLE,
        as_of=AS_OF,
    )


def evidence(
    count: int = 2,
    *,
    stable: bool = True,
    changing: bool = False,
) -> ValuationEvidenceState:
    return ValuationEvidenceState(
        credible_evidence_count=count,
        company_economics_stable=stable,
        company_economics_rapidly_changing=changing,
        available_at=AVAILABLE,
    )


def test_case1_valuation_produces_three_required_growth_cases_and_range():
    snapshot = build_case1_valuation(
        identity=identity("CASE1"),
        assumptions=assumptions(AnalysisCase.CASE_1_PROFITABLE_GROWTH),
        current_price=100,
        current_eps=5,
        required_return=0.15,
        evidence=evidence(),
        asymmetry_type=AsymmetryType.FAVORABLE,
    )
    cases = {case.band: case for case in snapshot.output.required_growth_cases}
    expected_base = ((100 * 1.15**3) / (5 * 15)) ** (1 / 3) - 1
    assert len(cases) == 3
    assert cases[ExitMultipleBand.BASE].required_growth == pytest.approx(expected_base)
    assert snapshot.output.required_growth == pytest.approx(expected_base)
    assert snapshot.output.required_growth_range.low == pytest.approx(
        cases[ExitMultipleBand.PREMIUM].required_growth
    )
    assert snapshot.output.required_growth_range.high == pytest.approx(
        cases[ExitMultipleBand.CONSERVATIVE].required_growth
    )


def test_case1_valuation_refuses_non_pe_primary_metric():
    with pytest.raises(ValueError, match="supports PE only"):
        build_case1_valuation(
            identity=identity(),
            assumptions=assumptions(
                AnalysisCase.CASE_1_PROFITABLE_GROWTH,
                metric=ValuationMetric.EV_EBIT,
            ),
            current_price=100,
            current_eps=5,
            required_return=0.15,
            evidence=evidence(),
            asymmetry_type=AsymmetryType.FAVORABLE,
        )


@pytest.mark.parametrize(
    ("plausible", "expected"),
    [
        ((0.50, 0.60), "positive"),
        ((-0.20, -0.10), "negative"),
        ((0.10, 0.30), "overlap"),
    ],
)
def test_case1_valuation_expectation_gap(plausible, expected):
    snapshot = build_case1_valuation(
        identity=identity(),
        assumptions=assumptions(
            AnalysisCase.CASE_1_PROFITABLE_GROWTH,
            plausible=plausible,
        ),
        current_price=100,
        current_eps=5,
        required_return=0.15,
        evidence=evidence(),
        asymmetry_type=AsymmetryType.FAVORABLE,
    )
    assert snapshot.output.expectation_gap.value == expected


@pytest.mark.parametrize(
    ("metric", "stage", "expected_revenue"),
    [
        (ValuationMetric.EV_REVENUE, TerminalStage.GROWTH, lambda ev, multiple: ev / multiple),
        (
            ValuationMetric.EV_GROSS_PROFIT,
            TerminalStage.GROWTH,
            lambda ev, multiple: ev / multiple / 0.50,
        ),
        (
            ValuationMetric.EV_EBIT,
            TerminalStage.TRANSITION,
            lambda ev, multiple: ev / multiple / 0.20,
        ),
    ],
)
def test_case2_valuation_terminal_metric_formulas(metric, stage, expected_revenue):
    snapshot = build_case2_valuation(
        identity=identity(),
        assumptions=assumptions(
            AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
            metric=metric,
            stage=stage,
            multiples=(4, 5, 6),
        ),
        current_market_cap=500,
        current_price=5,
        current_revenue=50,
        current_share_count=100,
        required_return=0.15,
        evidence=evidence(),
        asymmetry_type=AsymmetryType.BALANCED,
    )
    base = next(
        case
        for case in snapshot.output.required_growth_cases
        if case.band == ExitMultipleBand.BASE
    )
    assert base.required_future_equity_value == pytest.approx(500 * 1.15**5 * 1.05**5)
    assert base.required_future_enterprise_value == pytest.approx(
        base.required_future_equity_value + 20
    )
    assert base.required_future_revenue == pytest.approx(
        expected_revenue(base.required_future_enterprise_value, 5)
    )


def test_case2_valuation_dilution_and_terminal_debt_raise_required_growth():
    base_kwargs = dict(
        identity=identity(),
        current_market_cap=500,
        current_price=5,
        current_revenue=50,
        current_share_count=100,
        required_return=0.15,
        evidence=evidence(),
        asymmetry_type=AsymmetryType.BALANCED,
    )
    low = build_case2_valuation(
        assumptions=assumptions(
            AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
            dilution=0,
            terminal_net_debt=0,
            multiples=(4, 5, 6),
        ),
        **base_kwargs,
    )
    high = build_case2_valuation(
        assumptions=assumptions(
            AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
            dilution=0.10,
            terminal_net_debt=100,
            multiples=(4, 5, 6),
        ),
        **base_kwargs,
    )
    assert high.output.required_growth > low.output.required_growth


@pytest.mark.parametrize(
    ("evidence_state", "terminal_confidence", "expected"),
    [
        (evidence(2), ValuationConfidence.HIGH, ValuationConfidence.HIGH),
        (evidence(2, stable=False), ValuationConfidence.MEDIUM, ValuationConfidence.MEDIUM),
        (evidence(2, stable=False, changing=True), ValuationConfidence.HIGH, ValuationConfidence.LOW),
        (evidence(0, stable=False), ValuationConfidence.HIGH, ValuationConfidence.UNRESOLVED),
    ],
)
def test_valuation_confidence_states(evidence_state, terminal_confidence, expected):
    snapshot = build_case1_valuation(
        identity=identity(),
        assumptions=assumptions(
            AnalysisCase.CASE_1_PROFITABLE_GROWTH,
            confidence=terminal_confidence,
        ),
        current_price=100,
        current_eps=5,
        required_return=0.15,
        evidence=evidence_state,
        asymmetry_type=AsymmetryType.FAVORABLE,
    )
    assert snapshot.output.confidence == expected


def test_price_only_case2_recalculation_preserves_assumption_version():
    configured = assumptions(AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH)
    first = build_case2_valuation(
        identity=identity(),
        assumptions=configured,
        current_market_cap=500,
        current_price=5,
        current_revenue=50,
        current_share_count=100,
        required_return=0.15,
        evidence=evidence(),
        asymmetry_type=AsymmetryType.BALANCED,
    )
    second = build_case2_valuation(
        identity=identity(),
        assumptions=configured,
        current_market_cap=600,
        current_price=6,
        current_revenue=50,
        current_share_count=100,
        required_return=0.15,
        evidence=evidence(),
        asymmetry_type=AsymmetryType.BALANCED,
    )
    assert first.assumption_set is configured
    assert second.assumption_set is configured
    assert second.assumption_set.version == 7
    assert second.output.required_growth > first.output.required_growth


def quant_snapshot(case: AnalysisCase, grade: Grade) -> QuantSnapshot:
    return QuantSnapshot(
        snapshot_id="quant",
        ticker="SYNTH",
        case=case,
        model_version="frozen",
        period_end=PERIOD_END,
        available_at=AVAILABLE,
        as_of=AS_OF,
        metrics=(
            MetricResult(
                name="synthetic_core",
                state=ResolutionState.RESOLVED,
                value=1,
                grade=grade,
                weight=1,
            ),
        ),
        state=ResolutionState.RESOLVED,
        score=3,
        uncapped_grade=grade,
        grade=grade,
    )


def current_snapshot(
    case: AnalysisCase,
    overall: DirectionState,
    flags: frozenset[TrendFlag] = frozenset(),
) -> CurrentTrendSnapshot:
    return CurrentTrendSnapshot(
        snapshot_id="current",
        ticker="SYNTH",
        case=case,
        model_version="frozen",
        period_end=PERIOD_END,
        available_at=AVAILABLE,
        as_of=AS_OF,
        signals=(CurrentTrendSignal(name="synthetic", state=overall),),
        overall=overall,
        flags=flags,
    )


def valuation_snapshot(
    case: AnalysisCase,
    *,
    confidence: ValuationConfidence = ValuationConfidence.HIGH,
    resolved: bool = True,
) -> ValuationSnapshot:
    output = (
        ValuationOutput(
            required_growth=0.20,
            expectation_gap="positive",
            asymmetry_type=AsymmetryType.FAVORABLE,
            confidence=confidence,
        )
        if resolved
        else ValuationOutput()
    )
    kwargs = dict(market_price=100) if case == AnalysisCase.CASE_1_PROFITABLE_GROWTH else dict(market_cap=500)
    return ValuationSnapshot(
        snapshot_id="valuation",
        ticker="SYNTH",
        period_end=PERIOD_END,
        available_at=AVAILABLE,
        as_of=AS_OF,
        assumption_set=assumptions(case),
        state=ResolutionState.RESOLVED if resolved else ResolutionState.UNRESOLVED,
        output=output,
        **kwargs,
    )


def grade_result(
    case: AnalysisCase,
    quant_grade: Grade,
    *,
    current: CurrentTrendSnapshot | None = None,
    narrative_gate: NarrativeGate | None = None,
    valuation: ValuationSnapshot | None = None,
    breaker: bool = False,
):
    return build_investment_grade(
        snapshot_id="investment",
        ticker="SYNTH",
        period_end=PERIOD_END,
        available_at=AVAILABLE,
        as_of=AS_OF,
        case=case,
        quant=quant_snapshot(case, quant_grade),
        current_trend=current,
        narrative_gate=narrative_gate,
        valuation=valuation or valuation_snapshot(case),
        thesis_breaker_triggered=breaker,
    )


@pytest.mark.parametrize(
    ("quant_grade", "expected"),
    [(Grade.C, InvestmentGrade.B), (Grade.D, InvestmentGrade.C), (Grade.X, InvestmentGrade.D)],
)
def test_case1_every_quant_cap(quant_grade, expected):
    result = grade_result(AnalysisCase.CASE_1_PROFITABLE_GROWTH, quant_grade)
    assert result.initial_valuation_grade == InvestmentGrade.A
    assert result.final_grade == expected


def test_case1_current_low_confidence_and_deterioration_caps():
    case = AnalysisCase.CASE_1_PROFITABLE_GROWTH
    mixed = grade_result(case, Grade.A, current=current_snapshot(case, DirectionState.MIXED))
    negative = grade_result(case, Grade.A, current=current_snapshot(case, DirectionState.NEGATIVE))
    deterioration = grade_result(
        case,
        Grade.A,
        current=current_snapshot(
            case,
            DirectionState.NEGATIVE,
            frozenset({TrendFlag.COMMERCIAL_DETERIORATION}),
        ),
    )
    low = grade_result(case, Grade.A, valuation=valuation_snapshot(case, confidence=ValuationConfidence.LOW))
    assert mixed.final_grade == InvestmentGrade.B
    assert negative.final_grade == InvestmentGrade.C
    assert deterioration.final_grade == InvestmentGrade.D
    assert low.final_grade == InvestmentGrade.B


@pytest.mark.parametrize(
    ("gate", "expected"),
    [
        (NarrativeGate.QUALIFIED, InvestmentGrade.B),
        (NarrativeGate.DEVELOPING, InvestmentGrade.C),
        (NarrativeGate.WEAK, InvestmentGrade.D),
    ],
)
def test_case2_narrative_caps(gate, expected):
    result = grade_result(
        AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        Grade.A,
        narrative_gate=gate,
    )
    assert result.final_grade == expected


def test_case2_quant_x_inflection_exception_is_max_c():
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
    current = current_snapshot(
        case,
        DirectionState.POSITIVE,
        frozenset({TrendFlag.COMMERCIAL_INFLECTION}),
    )
    result = grade_result(
        case,
        Grade.X,
        current=current,
        narrative_gate=NarrativeGate.QUALIFIED,
    )
    assert result.final_grade == InvestmentGrade.C


def test_case2_funding_stress_and_commercial_deterioration_caps_record_order():
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
    result = grade_result(
        case,
        Grade.A,
        current=current_snapshot(
            case,
            DirectionState.NEGATIVE,
            frozenset(
                {TrendFlag.FUNDING_STRESS, TrendFlag.COMMERCIAL_DETERIORATION}
            ),
        ),
        narrative_gate=NarrativeGate.CONFIRMED,
    )
    assert result.final_grade == InvestmentGrade.D
    assert [adjustment.sequence for adjustment in result.adjustments] == list(
        range(1, len(result.adjustments) + 1)
    )
    assert [adjustment.trigger for adjustment in result.adjustments] == [
        InvestmentGradeTrigger.CURRENT_TREND,
        InvestmentGradeTrigger.COMMERCIAL_DETERIORATION,
        InvestmentGradeTrigger.FUNDING_STRESS,
    ]


def test_global_thesis_breaker_x_precedes_unresolved_valuation_u():
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
    result = grade_result(
        case,
        Grade.A,
        narrative_gate=NarrativeGate.BROKEN,
        valuation=valuation_snapshot(case, resolved=False),
        breaker=True,
    )
    assert result.initial_valuation_grade == InvestmentGrade.U
    assert result.final_grade == InvestmentGrade.X
    assert result.adjustments[0].trigger == InvestmentGradeTrigger.THESIS_BREAKER


def test_unresolved_valuation_returns_u_without_recomputing_upstream_results():
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
    result = grade_result(
        case,
        Grade.B,
        narrative_gate=NarrativeGate.CONFIRMED,
        valuation=valuation_snapshot(case, resolved=False),
    )
    assert result.initial_valuation_grade == InvestmentGrade.U
    assert result.final_grade == InvestmentGrade.U
