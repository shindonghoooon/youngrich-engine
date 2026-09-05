from datetime import date, datetime, timezone

import pytest

from engine.case2_analysis import Case2AnalysisInput, build_case2_analysis
from engine.case2_current import Case2CurrentInput
from engine.case2_quant import Case2AnnualPeriod, Case2QuantInput
from engine.investment_grade_engine import build_investment_grade
from engine.models import CapitalModel, Grade
from engine.tracking_models import (
    AnalysisCase,
    AnalysisSnapshot,
    AsymmetryType,
    AssumptionRange,
    DirectionState,
    ExitMultipleAssumption,
    ExitMultipleBand,
    ExitMultipleEvidenceSource,
    GrowthScope,
    InvestmentGrade,
    MetricResult,
    NarrativeAssessment,
    NarrativeGate,
    NarrativeSnapshot,
    NarrativeState,
    QuantSnapshot,
    ResolutionState,
    TerminalStage,
    TrendFlag,
    ValuationAssumptionSet,
    ValuationConfidence,
    ValuationMetric,
)
from engine.valuation_engine import (
    ValuationEvidenceState,
    ValuationIdentity,
    build_case1_valuation,
)


UTC = timezone.utc
ANNUAL_AVAILABLE = datetime(2026, 2, 15, tzinfo=UTC)
CURRENT_AVAILABLE = datetime(2026, 8, 1, tzinfo=UTC)
AS_OF = datetime(2026, 9, 1, tzinfo=UTC)


def exit_multiples(
    metric: ValuationMetric,
    values: tuple[float, float, float],
) -> tuple[ExitMultipleAssumption, ...]:
    return tuple(
        ExitMultipleAssumption(
            band=band,
            metric_type=metric,
            value=value,
            evidence_type=ExitMultipleEvidenceSource.COMPARABLE_COMPANIES,
            source_reference=f"synthetic-{band.value}",
            as_of=AS_OF,
            rationale="synthetic end-to-end fixture",
        )
        for band, value in zip(ExitMultipleBand, values, strict=True)
    )


def narrative(
    ticker: str,
    gate_profile: NarrativeGate,
) -> NarrativeSnapshot:
    if gate_profile == NarrativeGate.QUALIFIED:
        states = {
            "differentiation": NarrativeState.STRONG,
            "defensibility": NarrativeState.EMERGING,
            "adoption": NarrativeState.STRONG,
            "durability": NarrativeState.EMERGING,
        }
    elif gate_profile == NarrativeGate.WEAK:
        states = {"adoption": NarrativeState.WEAK}
    else:
        states = {
            "differentiation": NarrativeState.PROVEN,
            "defensibility": NarrativeState.PROVEN,
            "adoption": NarrativeState.PROVEN,
            "durability": NarrativeState.PROVEN,
        }
    dimensions = (
        "differentiation",
        "defensibility",
        "adoption",
        "penetration_expansion",
        "durability",
        "failure_mode",
    )
    return NarrativeSnapshot(
        snapshot_id=f"{ticker}-narrative",
        ticker=ticker,
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-narrative-v1-frozen",
        thesis_id=f"{ticker}-thesis",
        thesis_version=1,
        kpi_set_version=1,
        kpi_definition_ids=(f"{ticker}-kpi-1", f"{ticker}-kpi-2"),
        assessments=tuple(
            NarrativeAssessment(
                dimension=dimension,
                state=states.get(dimension, NarrativeState.EMERGING),
            )
            for dimension in dimensions
        ),
        overall=NarrativeState.EMERGING,
        period_end=date(2025, 12, 31),
        available_at=ANNUAL_AVAILABLE,
        as_of=AS_OF,
    )


def annual(
    year: int,
    revenue: float,
    gross_profit: float,
    *,
    cfo: float,
    capex: float,
    liquidity: float,
    shares: float,
) -> Case2AnnualPeriod:
    return Case2AnnualPeriod(
        fiscal_year=year,
        fiscal_period_end=date(year, 12, 31),
        revenue=revenue,
        gross_profit=gross_profit,
        operating_income=-10,
        cfo=cfo,
        growth_capex=capex,
        liquidity=liquidity,
        actual_common_shares=shares,
    )


def case2_assumptions(
    ticker: str,
    *,
    confidence: ValuationConfidence = ValuationConfidence.HIGH,
) -> ValuationAssumptionSet:
    return ValuationAssumptionSet(
        assumption_set_id=f"{ticker}-valuation-assumptions",
        version=1,
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        horizon_years=5,
        terminal_stage=TerminalStage.GROWTH,
        terminal_stage_rationale="synthetic emerging-growth horizon",
        terminal_stage_confidence=confidence,
        primary_metric=ValuationMetric.EV_REVENUE,
        exit_multiples=exit_multiples(ValuationMetric.EV_REVENUE, (4, 5, 6)),
        plausible_growth_range=AssumptionRange(low=2.0, high=3.0),
        expected_annual_dilution=0.05,
        terminal_net_debt=10,
    )


def analysis_input(
    *,
    ticker: str,
    periods: tuple[Case2AnnualPeriod, ...],
    gate: NarrativeGate,
    current_overrides: dict | None = None,
    breaker: bool = False,
    evidence_count: int = 2,
) -> Case2AnalysisInput:
    current_values = dict(
        snapshot_id=f"{ticker}-current",
        ticker=ticker,
        period_end=date(2026, 6, 30),
        available_at=CURRENT_AVAILABLE,
        as_of=AS_OF,
        growth_scope=GrowthScope.SAME_SCOPE,
        annual_quant_grade=None,
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
        thesis_breaker_triggered=breaker,
    )
    current_values.update(current_overrides or {})
    return Case2AnalysisInput(
        snapshot_id=f"{ticker}-analysis",
        investment_grade_snapshot_id=f"{ticker}-investment",
        company_name=f"{ticker} synthetic profile",
        period_end=date(2026, 6, 30),
        available_at=CURRENT_AVAILABLE,
        as_of=AS_OF,
        quant=Case2QuantInput(
            snapshot_id=f"{ticker}-quant",
            ticker=ticker,
            periods=periods,
            period_end=periods[-1].fiscal_period_end,
            available_at=ANNUAL_AVAILABLE,
            as_of=AS_OF,
            growth_scope=GrowthScope.SAME_SCOPE,
            core_revenue_representative=True,
            commercial_evidence_exists=True,
            potential_dilution="synthetic-watch",
        ),
        narrative=narrative(ticker, gate),
        commercial_evidence_exists=True,
        thesis_breaker_triggered=breaker,
        current=Case2CurrentInput(**current_values),
        valuation_assumptions=case2_assumptions(ticker),
        current_market_cap=200,
        current_price=2,
        current_revenue=periods[-1].revenue,
        current_share_count=100,
        required_return=0.15,
        valuation_evidence=ValuationEvidenceState(
            credible_evidence_count=evidence_count,
            company_economics_stable=True,
            company_economics_rapidly_changing=False,
            available_at=CURRENT_AVAILABLE,
        ),
        asymmetry_type=AsymmetryType.FAVORABLE,
    )


@pytest.fixture
def tem_like_periods() -> tuple[Case2AnnualPeriod, ...]:
    return (
        annual(2023, 60, 25, cfo=-20, capex=5, liquidity=30, shares=98),
        annual(2024, 75, 32, cfo=-15, capex=5, liquidity=35, shares=100),
        annual(2025, 100, 45, cfo=-10, capex=5, liquidity=37.5, shares=102),
    )


def test_case1_full_synthetic_analysis_fixture():
    weights = (0.15, 0.15, 0.10, 0.10, 0.20, 0.10, 0.05, 0.15)
    quant = QuantSnapshot(
        snapshot_id="case1-quant",
        ticker="CASE1",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        model_version="case1-quant-v1-frozen",
        period_end=date(2025, 12, 31),
        available_at=ANNUAL_AVAILABLE,
        as_of=AS_OF,
        metrics=tuple(
            MetricResult(
                name=f"core-{index}",
                state=ResolutionState.RESOLVED,
                value=0.20,
                grade=Grade.A,
                weight=weight,
            )
            for index, weight in enumerate(weights)
        ),
        state=ResolutionState.RESOLVED,
        score=4.0,
        uncapped_grade=Grade.A,
        grade=Grade.A,
    )
    valuation_assumptions = ValuationAssumptionSet(
        assumption_set_id="case1-assumptions",
        version=1,
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        horizon_years=3,
        terminal_stage=TerminalStage.MATURE,
        terminal_stage_rationale="synthetic profitable-growth horizon",
        terminal_stage_confidence=ValuationConfidence.HIGH,
        primary_metric=ValuationMetric.PE,
        exit_multiples=exit_multiples(ValuationMetric.PE, (12, 16, 20)),
        plausible_growth_range=AssumptionRange(low=0.50, high=0.60),
    )
    valuation = build_case1_valuation(
        identity=ValuationIdentity(
            snapshot_id="case1-valuation",
            ticker="CASE1",
            period_end=date(2026, 6, 30),
            available_at=CURRENT_AVAILABLE,
            as_of=AS_OF,
        ),
        assumptions=valuation_assumptions,
        current_price=100,
        current_eps=5,
        required_return=0.15,
        evidence=ValuationEvidenceState(
            credible_evidence_count=2,
            company_economics_stable=True,
            company_economics_rapidly_changing=False,
            available_at=CURRENT_AVAILABLE,
        ),
        asymmetry_type=AsymmetryType.FAVORABLE,
    )
    grade = build_investment_grade(
        snapshot_id="case1-investment",
        ticker="CASE1",
        period_end=date(2026, 6, 30),
        available_at=CURRENT_AVAILABLE,
        as_of=AS_OF,
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        quant=quant,
        current_trend=None,
        narrative_gate=None,
        valuation=valuation,
        thesis_breaker_triggered=False,
    )
    snapshot = AnalysisSnapshot(
        snapshot_id="case1-analysis",
        ticker="CASE1",
        company_name="Synthetic Profitable Growth",
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        case_definition_version="case1-v1-frozen",
        capital_model=CapitalModel.ASSET_LIGHT,
        period_end=date(2026, 6, 30),
        available_at=CURRENT_AVAILABLE,
        as_of=AS_OF,
        quant=quant,
        valuation=valuation,
        investment_grade=grade,
    )
    assert snapshot.quant.grade == Grade.A
    assert snapshot.investment_grade.final_grade == InvestmentGrade.A


def test_tem_like_case2_b_scenario(tem_like_periods):
    snapshot = build_case2_analysis(
        analysis_input(
            ticker="TEM_LIKE",
            periods=tem_like_periods,
            gate=NarrativeGate.QUALIFIED,
        )
    )
    assert snapshot.quant.grade == Grade.B
    assert snapshot.investment_grade.final_grade == InvestmentGrade.B


def test_ionq_like_funding_stress_speculative_d_scenario(tem_like_periods):
    snapshot = build_case2_analysis(
        analysis_input(
            ticker="IONQ_LIKE",
            periods=tem_like_periods,
            gate=NarrativeGate.WEAK,
            current_overrides={
                "current_cfo": -40,
                "current_growth_capex": 10,
                "prior_comparable_cfo": -10,
                "prior_comparable_growth_capex": 5,
                "current_runway_months": 5,
                "actual_shares_growth": 0.25,
            },
        )
    )
    assert TrendFlag.FUNDING_STRESS in snapshot.current_trend.flags
    assert snapshot.investment_grade.final_grade == InvestmentGrade.D


def test_lpth_like_quant_x_inflection_is_c():
    weak_periods = (
        annual(2023, 100, 40, cfo=-5, capex=5, liquidity=10, shares=100),
        annual(2024, 100, 40, cfo=-5, capex=5, liquidity=10, shares=100),
        annual(2025, 90, 35, cfo=-25, capex=5, liquidity=5, shares=100),
    )
    snapshot = build_case2_analysis(
        analysis_input(
            ticker="LPTH_LIKE",
            periods=weak_periods,
            gate=NarrativeGate.QUALIFIED,
        )
    )
    assert snapshot.quant.grade == Grade.X
    assert TrendFlag.COMMERCIAL_INFLECTION in snapshot.current_trend.flags
    assert snapshot.investment_grade.final_grade == InvestmentGrade.C


def test_broken_thesis_scenario_is_x(tem_like_periods):
    snapshot = build_case2_analysis(
        analysis_input(
            ticker="BROKEN",
            periods=tem_like_periods,
            gate=NarrativeGate.CONFIRMED,
            breaker=True,
        )
    )
    assert snapshot.investment_grade.final_grade == InvestmentGrade.X


def test_unresolved_valuation_scenario_is_u(tem_like_periods):
    snapshot = build_case2_analysis(
        analysis_input(
            ticker="VALUATION_U",
            periods=tem_like_periods,
            gate=NarrativeGate.CONFIRMED,
            evidence_count=0,
        )
    )
    assert snapshot.valuation.output.confidence == ValuationConfidence.UNRESOLVED
    assert snapshot.investment_grade.final_grade == InvestmentGrade.U
