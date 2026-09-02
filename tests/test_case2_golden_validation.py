"""Golden validation against manually curated, source-timestamped public data.

The reference functions in this module intentionally do not call production policy
helpers.  They duplicate the frozen arithmetic in small, explicit test code so a
production regression cannot make both sides of the comparison pass tautologically.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path

import pytest

from engine.case2_analysis import Case2AnalysisInput, build_case2_analysis
from engine.case2_current import Case2CurrentInput
from engine.case2_quant import Case2AnnualPeriod, Case2QuantInput
from engine.models import Grade
from engine.narrative_engine import derive_gate_from_snapshot
from engine.tracking_models import (
    AnalysisCase,
    AsymmetryType,
    AssumptionRange,
    DirectionState,
    ExitMultipleAssumption,
    ExitMultipleBand,
    ExitMultipleEvidenceSource,
    GrowthScope,
    InvestmentGrade,
    NarrativeAssessment,
    NarrativeGate,
    NarrativeSnapshot,
    NarrativeState,
    ResolutionState,
    TerminalStage,
    TrendFlag,
    ValuationAssumptionSet,
    ValuationConfidence,
    ValuationMetric,
)
from engine.valuation_engine import ValuationEvidenceState


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "case2_real_world"
TICKERS = ("TEM", "IONQ", "ONDS", "LPTH", "EROC")
WEIGHTS = {
    "revenue_growth": 0.30,
    "gross_profit_growth": 0.15,
    "cash_burn_trend": 0.15,
    "runway": 0.15,
    "dilution": 0.15,
    "revenue_per_share_growth": 0.10,
}
POINTS = {"A": 4, "B": 3, "C": 2, "D": 1, "X": 0}


def load_fixture(ticker: str) -> dict:
    return json.loads((FIXTURE_DIR / f"{ticker}.json").read_text(encoding="utf-8"))


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def reference_cagr(latest: float | None, first: float | None) -> float | None:
    if latest is None or first is None or latest <= 0 or first <= 0:
        return None
    return math.sqrt(latest / first) - 1


def threshold_grade(value: float | None, thresholds: tuple[tuple[float, str], ...]) -> str | None:
    if value is None:
        return None
    for threshold, grade in thresholds:
        if value >= threshold:
            return grade
    return "X"


def reference_quant(data: dict) -> dict:
    first, previous, latest = data["annual"]["periods"]
    revenue_growth = reference_cagr(latest["revenue"], first["revenue"])
    gp_growth = reference_cagr(latest["gross_profit"], first["gross_profit"])
    previous_fcf = None if previous["cfo"] is None or previous["growth_capex"] is None else previous["cfo"] - previous["growth_capex"]
    latest_fcf = None if latest["cfo"] is None or latest["growth_capex"] is None else latest["cfo"] - latest["growth_capex"]

    if latest_fcf is None or previous_fcf is None:
        burn_grade = None
        burn_value = None
    elif latest_fcf >= 0:
        burn_grade = "A"
        burn_value = "burning_to_positive" if previous_fcf < 0 else "fcf_positive"
    elif previous_fcf >= 0:
        burn_grade, burn_value = "X", "positive_to_burning"
    else:
        burn_change = ((-latest_fcf) - (-previous_fcf)) / (-previous_fcf)
        burn_value = burn_change
        burn_reduction = -burn_change
        if burn_reduction >= 0.30:
            burn_grade = "A"
        elif burn_reduction >= 0.10:
            burn_grade = "B"
        elif burn_change <= 0.10:
            burn_grade = "C"
        elif burn_change <= 0.50:
            burn_grade = "D"
        else:
            burn_grade = "X"

    if latest_fcf is None:
        runway, runway_grade = None, None
    elif latest_fcf >= 0:
        runway, runway_grade = math.inf, "A"
    elif latest["liquidity"] is None:
        runway, runway_grade = None, None
    else:
        runway = latest["liquidity"] / (-latest_fcf) * 12
        runway_grade = threshold_grade(runway, ((36, "A"), (24, "B"), (12, "C"), (6, "D")))

    shares_valid = data["annual"]["share_comparison_valid"]
    if shares_valid and latest["actual_common_shares"] and previous["actual_common_shares"]:
        dilution = latest["actual_common_shares"] / previous["actual_common_shares"] - 1
        revenue_per_share_growth = (
            (latest["revenue"] / latest["actual_common_shares"])
            / (previous["revenue"] / previous["actual_common_shares"])
            - 1
        )
    else:
        dilution = revenue_per_share_growth = None

    grades = {
        "revenue_growth": threshold_grade(revenue_growth, ((0.40, "A"), (0.25, "B"), (0.15, "C"), (0.0, "D"))),
        "gross_profit_growth": threshold_grade(gp_growth, ((0.45, "A"), (0.30, "B"), (0.15, "C"), (0.0, "D"))),
        "cash_burn_trend": burn_grade,
        "runway": runway_grade,
        "dilution": None if dilution is None else ("A" if dilution <= 0.02 else "B" if dilution <= 0.05 else "C" if dilution <= 0.10 else "D" if dilution <= 0.20 else "X"),
        "revenue_per_share_growth": threshold_grade(revenue_per_share_growth, ((0.30, "A"), (0.20, "B"), (0.10, "C"), (0.0, "D"))),
    }
    resolved_weight = sum(WEIGHTS[name] for name, grade in grades.items() if grade is not None)
    mandatory_resolved = all(grades[name] is not None for name in ("revenue_growth", "gross_profit_growth", "cash_burn_trend", "runway"))
    eligible = (
        latest["revenue"] is not None and latest["revenue"] > 0
        and latest["gross_profit"] is not None and latest["gross_profit"] > 0
        and latest["operating_income"] is not None and latest["operating_income"] < 0
        and data["annual"]["core_revenue_representative"] is True
        and data["annual"]["commercial_evidence_exists"] is True
    )
    if not mandatory_resolved or not eligible:
        score = uncapped = final = None
    else:
        score = sum(POINTS[grade] * WEIGHTS[name] for name, grade in grades.items() if grade is not None) / resolved_weight
        uncapped = "A" if score >= 3.50 else "B" if score >= 3.00 else "C" if score >= 2.40 else "D" if score >= 1.80 else "X"
        final = "D" if grades["cash_burn_trend"] == "X" and grades["dilution"] == "X" and uncapped in {"A", "B", "C"} else uncapped
    return {
        "values": {"revenue_growth": revenue_growth, "gross_profit_growth": gp_growth, "cash_burn_trend": burn_value, "runway": runway, "dilution": dilution, "revenue_per_share_growth": revenue_per_share_growth},
        "grades": grades, "score": score, "uncapped_grade": uncapped, "final_grade": final,
        "coverage": resolved_weight, "latest_fcf": latest_fcf, "previous_fcf": previous_fcf,
    }


def reference_current(data: dict, annual: dict) -> dict:
    current = data["current"]
    growth = lambda value, prior: None if value is None or prior is None or prior <= 0 else value / prior - 1
    momentum = lambda value: "unresolved" if value is None else "positive" if value >= 0.25 else "neutral" if value >= 0.10 else "negative"
    revenue_growth = growth(current["current_revenue"], current["prior_revenue"])
    gp_growth = growth(current["current_gross_profit"], current["prior_gross_profit"])
    current_fcf = current["current_cfo"] - current["current_growth_capex"]
    prior_fcf = current["prior_cfo"] - current["prior_growth_capex"]
    if current_fcf >= 0:
        cash = "positive"
        deterioration = None
    elif prior_fcf >= 0:
        cash, deterioration = "negative", math.inf
    else:
        deterioration = ((-current_fcf) - (-prior_fcf)) / (-prior_fcf)
        cash = "positive" if deterioration <= -0.20 else "neutral" if deterioration <= 0.20 else "negative"
    if current["prior_actual_shares"] is None:
        share_growth = None
    else:
        share_growth = current["current_actual_shares"] / current["prior_actual_shares"] - 1
    annual_fcf = annual["latest_fcf"]
    runway = math.inf if annual_fcf is not None and annual_fcf >= 0 else None if annual_fcf is None else current["current_liquidity"] / (-annual_fcf) * 12
    funding = "unresolved" if runway is None or share_growth is None else "positive" if runway >= 24 and share_growth <= 0.05 else "neutral" if runway >= 12 and share_growth <= 0.15 else "negative"
    kpis = [state for state in current["primary_kpi_states"] if state != "unresolved"]
    if len(kpis) < 2:
        thesis = "unresolved"
    else:
        thesis = "positive" if kpis.count("positive") > kpis.count("negative") else "negative" if kpis.count("negative") > kpis.count("positive") else "neutral"
    signals = (momentum(revenue_growth), momentum(gp_growth), cash, funding, thesis)
    resolved = [state for state in signals if state != "unresolved"]
    positive, negative = resolved.count("positive"), resolved.count("negative")
    overall = "unresolved" if len(resolved) < 4 else "strong_positive" if positive >= 4 and negative == 0 else "mixed" if positive >= 2 and negative >= 2 else "positive" if positive >= 3 and negative <= 1 else "negative" if negative >= 3 and positive <= 1 else "neutral"
    funding_stress = bool(deterioration is not None and share_growth is not None and deterioration > 0.50 and share_growth > 0.20)
    inflection = annual["final_grade"] in {None, "D", "X"} and signals[0] == signals[1] == signals[4] == "positive"
    deterioration_flag = annual["final_grade"] in {"A", "B"} and signals[0] == signals[1] == signals[4] == "negative"
    annual_growth = annual["values"]["revenue_growth"]
    acceleration = "unresolved" if revenue_growth is None or annual_growth is None else "accelerating" if revenue_growth - annual_growth >= 0.10 else "decelerating" if revenue_growth - annual_growth <= -0.10 else "stable"
    return {"signals": signals, "overall": overall, "funding_stress": funding_stress, "commercial_inflection": inflection, "commercial_deterioration": deterioration_flag, "acceleration": acceleration, "runway": runway, "share_growth": share_growth}


def reference_narrative_gate(data: dict) -> str:
    axes = data["narrative"]["axes"]
    if data["narrative"]["thesis_breaker_triggered"]:
        return "broken"
    if axes["adoption"] == "weak":
        return "weak"
    if not data["narrative"]["commercial_evidence_exists"]:
        return "unresolved"
    strong = {"strong", "proven"}
    durable = {"emerging", "strong", "proven"}
    differentiated = axes["differentiation"] in strong or axes["defensibility"] in strong
    if axes["adoption"] in strong and axes["durability"] in strong and differentiated:
        return "confirmed"
    if axes["adoption"] in strong and axes["durability"] in durable and differentiated:
        return "qualified"
    return "developing"


def reference_valuation(data: dict) -> dict:
    valuation, market = data["valuation"], data["market"]
    market_cap = market["close"] * market["shares_for_market_cap"] / 1000
    future_equity = market_cap * (1 + valuation["required_return"]) ** valuation["horizon_years"] * (1 + valuation["expected_annual_dilution"]) ** valuation["horizon_years"]
    future_ev = future_equity + valuation["terminal_net_debt"]
    current_revenue = data["annual"]["periods"][-1]["revenue"]
    cases = []
    for multiple in valuation["exit_multiples"]:
        future_revenue = future_ev / multiple
        required_growth = (future_revenue / current_revenue) ** (1 / valuation["horizon_years"]) - 1
        cases.append((future_revenue, required_growth))
    required_range = (min(item[1] for item in cases), max(item[1] for item in cases))
    plausible = valuation["plausible_growth_range"]
    gap = "positive" if plausible[0] > required_range[1] else "negative" if plausible[1] < required_range[0] else "overlap"
    confidence = "unresolved" if valuation["credible_evidence_count"] == 0 else "low" if valuation["credible_evidence_count"] == 1 or valuation["economics_rapidly_changing"] or valuation["terminal_stage_confidence"] == "low" else "high" if valuation["credible_evidence_count"] >= 2 and valuation["economics_stable"] and valuation["terminal_stage_confidence"] == "high" else "medium"
    return {"market_cap": market_cap, "future_equity": future_equity, "future_ev": future_ev, "cases": cases, "required_range": required_range, "gap": gap, "confidence": confidence}


def reference_investment_grade(quant: dict, current: dict, gate: str, valuation: dict) -> dict:
    if valuation["confidence"] == "unresolved" or valuation["gap"] == "unresolved":
        return {"initial": "U", "adjustments": (("valuation_confidence", "U"),), "final": "U"}
    asymmetry = None
    if valuation["gap"] == "positive":
        asymmetry = "favorable"
    if valuation["gap"] == "positive" and asymmetry == "favorable":
        initial = "A"
    elif valuation["gap"] == "overlap":
        initial = "B"
    elif valuation["gap"] == "negative" and valuation["confidence"] == "low":
        initial = "C"
    else:
        initial = "D"
    adjustments = []
    narrative_caps = {"qualified": "B", "developing": "C", "weak": "D", "broken": "X"}
    if gate in narrative_caps:
        adjustments.append(("narrative", narrative_caps[gate]))
    quant_caps = {"C": "B", "D": "C"}
    if quant["final_grade"] == "X":
        quant_cap = "C" if current["commercial_inflection"] and gate in {"confirmed", "qualified"} else "D"
        adjustments.append(("quant", quant_cap))
    elif quant["final_grade"] in quant_caps:
        adjustments.append(("quant", quant_caps[quant["final_grade"]]))
    if current["overall"] == "mixed":
        adjustments.append(("current_trend", "B"))
    elif current["overall"] == "negative":
        adjustments.append(("current_trend", "C"))
    if current["commercial_deterioration"]:
        adjustments.append(("commercial_deterioration", "D"))
    if current["funding_stress"]:
        adjustments.append(("funding_stress", "C"))
    if valuation["confidence"] == "low":
        adjustments.append(("valuation_confidence", "B"))
    order = {"A": 0, "B": 1, "C": 2, "D": 3, "X": 4}
    final = initial
    for _, cap in adjustments:
        if order[final] < order[cap]:
            final = cap
    return {"initial": initial, "adjustments": tuple(adjustments), "final": final}


def build_input(data: dict) -> Case2AnalysisInput:
    as_of = parse_datetime(data["analysis_as_of"])
    annual_source = data["sources"][data["annual"]["source_id"]]
    current_source = data["sources"][data["current"]["source_id"]]
    annual_ref = reference_quant(data)
    current_ref = reference_current(data, annual_ref)
    periods = tuple(Case2AnnualPeriod(**period) for period in data["annual"]["periods"])
    ticker = data["ticker"]
    axes = data["narrative"]["axes"]
    narrative = NarrativeSnapshot(
        snapshot_id=f"{ticker}-golden-narrative", ticker=ticker, case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-narrative-v1-frozen", thesis_id=f"{ticker}-validation-thesis", thesis_version=data["narrative"]["thesis_version"],
        kpi_set_version=data["narrative"]["kpi_set_version"], kpi_definition_ids=tuple(f"{ticker}-kpi-{i}" for i, _ in enumerate(data["current"]["primary_kpi_states"], 1)),
        assessments=tuple(NarrativeAssessment(dimension=name, state=NarrativeState(value), evidence=(data["sources"][data["narrative"]["source_id"]]["url"],)) for name, value in axes.items()),
        overall=NarrativeState.EMERGING, period_end=date.fromisoformat(data["current"]["period_end"]), available_at=parse_datetime(current_source["available_at"]), as_of=as_of,
    )
    metric = ValuationMetric(data["valuation"]["primary_metric"])
    assumptions = ValuationAssumptionSet(
        assumption_set_id=data["valuation"]["assumption_set_id"], version=1, case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        horizon_years=data["valuation"]["horizon_years"], terminal_stage=TerminalStage(data["valuation"]["terminal_stage"]), terminal_stage_rationale=data["valuation"]["rationale"],
        terminal_stage_confidence=ValuationConfidence(data["valuation"]["terminal_stage_confidence"]), primary_metric=metric,
        exit_multiples=tuple(ExitMultipleAssumption(band=band, metric_type=metric, value=value, evidence_type=ExitMultipleEvidenceSource.COMPARABLE_COMPANIES, source_reference="validation-only range; see fixture rationale", as_of=as_of, rationale=data["valuation"]["rationale"]) for band, value in zip(ExitMultipleBand, data["valuation"]["exit_multiples"], strict=True)),
        plausible_growth_range=AssumptionRange(low=data["valuation"]["plausible_growth_range"][0], high=data["valuation"]["plausible_growth_range"][1]),
        expected_annual_dilution=data["valuation"]["expected_annual_dilution"], terminal_net_debt=data["valuation"]["terminal_net_debt"], notes=("validation-only; not frozen company fair value",),
    )
    latest = periods[-1]
    market_cap = data["market"]["close"] * data["market"]["shares_for_market_cap"] / 1000
    return Case2AnalysisInput(
        snapshot_id=f"{ticker}-golden-analysis-2026-09-01", investment_grade_snapshot_id=f"{ticker}-golden-ig-2026-09-01", company_name=data["company_name"],
        period_end=date.fromisoformat(data["current"]["period_end"]), available_at=as_of, as_of=as_of,
        quant=Case2QuantInput(snapshot_id=f"{ticker}-golden-quant", ticker=ticker, periods=periods, period_end=date.fromisoformat(data["annual"]["period_end"]), available_at=parse_datetime(annual_source["available_at"]), as_of=as_of, growth_scope=GrowthScope(data["annual"]["growth_scope"]), core_revenue_representative=data["annual"]["core_revenue_representative"], commercial_evidence_exists=data["annual"]["commercial_evidence_exists"], share_comparison_valid=data["annual"]["share_comparison_valid"], potential_dilution="see source fixture"),
        narrative=narrative, commercial_evidence_exists=data["narrative"]["commercial_evidence_exists"], thesis_breaker_triggered=data["narrative"]["thesis_breaker_triggered"],
        current=Case2CurrentInput(snapshot_id=f"{ticker}-golden-current", ticker=ticker, period_end=date.fromisoformat(data["current"]["period_end"]), available_at=parse_datetime(current_source["available_at"]), as_of=as_of, growth_scope=GrowthScope(data["current"]["growth_scope"]), annual_quant_grade=None, annual_revenue_growth=annual_ref["values"]["revenue_growth"], current_revenue=data["current"]["current_revenue"], prior_comparable_revenue=data["current"]["prior_revenue"], current_gross_profit=data["current"]["current_gross_profit"], prior_comparable_gross_profit=data["current"]["prior_gross_profit"], current_cfo=data["current"]["current_cfo"], current_growth_capex=data["current"]["current_growth_capex"], prior_comparable_cfo=data["current"]["prior_cfo"], prior_comparable_growth_capex=data["current"]["prior_growth_capex"], current_runway_months=current_ref["runway"], actual_shares_growth=current_ref["share_growth"], primary_kpi_states=tuple(DirectionState(value) for value in data["current"]["primary_kpi_states"]), thesis_breaker_triggered=data["narrative"]["thesis_breaker_triggered"]),
        valuation_assumptions=assumptions, current_market_cap=market_cap, current_revenue=latest.revenue, required_return=data["valuation"]["required_return"],
        valuation_evidence=ValuationEvidenceState(credible_evidence_count=data["valuation"]["credible_evidence_count"], company_economics_stable=data["valuation"]["economics_stable"], company_economics_rapidly_changing=data["valuation"]["economics_rapidly_changing"]), asymmetry_type=AsymmetryType(data["valuation"]["asymmetry_type"]),
    )


@pytest.mark.parametrize("ticker", TICKERS)
def test_golden_fixture_provenance_and_look_ahead(ticker):
    data = load_fixture(ticker)
    as_of = parse_datetime(data["analysis_as_of"])
    assert data["unit"]
    for source in data["sources"].values():
        assert source["source"] and source["url"] and source["source_date"]
        assert parse_datetime(source["available_at"]) <= as_of
    for section in ("annual", "current"):
        assert data[section]["source_id"] in data["sources"]
        assert data[section]["period_end"]
        assert data[section]["retrieved_fields"]
        assert data[section]["normalization_note"]
    assert data["market"]["source_id"] in data["sources"]
    assert data["market"]["normalization_note"]


@pytest.mark.parametrize("ticker", TICKERS)
def test_golden_full_pipeline_matches_independent_reference(ticker):
    data = load_fixture(ticker)
    quant_ref = reference_quant(data)
    current_ref = reference_current(data, quant_ref)
    valuation_ref = reference_valuation(data)
    gate_ref = reference_narrative_gate(data)
    investment_ref = reference_investment_grade(quant_ref, current_ref, gate_ref, valuation_ref)
    snapshot = build_case2_analysis(build_input(data))

    metrics = {metric.name: metric for metric in snapshot.quant.metrics if metric.is_core}
    for name, expected in quant_ref["values"].items():
        if isinstance(expected, float):
            assert metrics[name].value == pytest.approx(expected)
        else:
            assert metrics[name].value == expected
        expected_grade = quant_ref["grades"][name]
        assert (metrics[name].grade.value if metrics[name].grade else None) == expected_grade
    assert snapshot.quant.score == pytest.approx(quant_ref["score"]) if quant_ref["score"] is not None else snapshot.quant.score is None
    assert (snapshot.quant.uncapped_grade.value if snapshot.quant.uncapped_grade else None) == quant_ref["uncapped_grade"]
    assert (snapshot.quant.grade.value if snapshot.quant.grade else None) == quant_ref["final_grade"]
    assert snapshot.quant.coverage == pytest.approx(quant_ref["coverage"])

    assert tuple(signal.state.value for signal in snapshot.current_trend.signals) == current_ref["signals"]
    assert snapshot.current_trend.overall.value == current_ref["overall"]
    assert (TrendFlag.FUNDING_STRESS in snapshot.current_trend.flags) is current_ref["funding_stress"]
    assert (TrendFlag.COMMERCIAL_INFLECTION in snapshot.current_trend.flags) is current_ref["commercial_inflection"]
    assert (TrendFlag.COMMERCIAL_DETERIORATION in snapshot.current_trend.flags) is current_ref["commercial_deterioration"]

    assert snapshot.valuation.market_cap == pytest.approx(valuation_ref["market_cap"])
    assert snapshot.valuation.output.confidence.value == valuation_ref["confidence"]
    assert snapshot.valuation.output.expectation_gap.value == valuation_ref["gap"]
    for output, (future_revenue, growth) in zip(snapshot.valuation.output.required_growth_cases, valuation_ref["cases"], strict=True):
        assert output.required_future_equity_value == pytest.approx(valuation_ref["future_equity"])
        assert output.required_future_enterprise_value == pytest.approx(valuation_ref["future_ev"])
        assert output.required_future_revenue == pytest.approx(future_revenue)
        assert output.required_growth == pytest.approx(growth)
    assert snapshot.valuation.output.required_growth == pytest.approx(valuation_ref["cases"][1][1])
    assert snapshot.narrative is not None
    gate = derive_gate_from_snapshot(
        snapshot.narrative,
        commercial_evidence_exists=data["narrative"]["commercial_evidence_exists"],
        thesis_breaker_triggered=data["narrative"]["thesis_breaker_triggered"],
    ).gate
    assert gate.value == gate_ref
    assert snapshot.investment_grade.initial_valuation_grade.value == investment_ref["initial"]
    assert tuple((item.trigger.value, item.maximum_grade.value) for item in snapshot.investment_grade.adjustments) == investment_ref["adjustments"]
    assert snapshot.investment_grade.final_grade.value == investment_ref["final"]


def test_golden_high_level_regressions():
    outputs = {ticker: build_case2_analysis(build_input(load_fixture(ticker))) for ticker in TICKERS}
    assert {ticker: (item.quant.grade.value if item.quant.grade else None) for ticker, item in outputs.items()} == {"TEM": "B", "IONQ": "D", "ONDS": "C", "LPTH": "X", "EROC": None}
    assert {ticker: item.current_trend.overall.value for ticker, item in outputs.items()} == {"TEM": "positive", "IONQ": "mixed", "ONDS": "mixed", "LPTH": "positive", "EROC": "neutral"}
    assert TrendFlag.FUNDING_STRESS in outputs["IONQ"].current_trend.flags
    assert TrendFlag.FUNDING_STRESS in outputs["ONDS"].current_trend.flags
    assert TrendFlag.COMMERCIAL_INFLECTION in outputs["LPTH"].current_trend.flags
    assert outputs["EROC"].quant.state == ResolutionState.UNRESOLVED
    assert outputs["EROC"].investment_grade.final_grade == InvestmentGrade.U
    assert {ticker: item.investment_grade.final_grade.value for ticker, item in outputs.items()} == {"TEM": "B", "IONQ": "C", "ONDS": "C", "LPTH": "C", "EROC": "U"}
