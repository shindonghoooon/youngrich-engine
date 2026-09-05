from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from engine.case1_snapshot import (
    CASE1_CORE_METRICS,
    build_case1_snapshot,
    validate_case1_core_metrics,
)
from engine.case2_current import Case2CurrentInput, build_case2_current_trend
from engine.case2_quant import (
    Case2AnnualPeriod,
    Case2QuantInput,
    validate_case2_quant_snapshot,
)
from engine.financial_metrics import cumulative_capex_to_cfo_3y
from engine.financials import FinancialHistory, load_financial_history
from engine.investment_grade_engine import build_investment_grade
from engine.investment_grade_engine_v1_1 import build_investment_grade_v1_1
from engine.limited_operating import load_demo_profile
from engine.models import CapitalModel, Grade
from engine.persistence.models import Base
from engine.persistence.mappers import analysis_from_row, analysis_to_rows
from engine.persistence.repositories import (
    AnalysisRepository,
    IdentityRepository,
    ValuationRepository,
)
from engine.persistence.schemas import Company, Instrument
from engine.persistence.session import create_session_factory, create_sqlite_engine
from engine.snapshot_diff import build_snapshot_diff
from engine.tracking_models import (
    AnalysisCase,
    AnalysisSnapshot,
    AsymmetryType,
    AssumptionRange,
    BinaryEvidenceState,
    DirectionState,
    ExitMultipleAssumption,
    ExitMultipleBand,
    ExitMultipleEvidenceSource,
    InvestmentGradePolicyVersion,
    MetricResult,
    ResolutionState,
    TerminalStage,
    TrendFlag,
    ValuationAssumptionSet,
    ValuationChangeType,
    ValuationConfidence,
    ValuationMetric,
)
from engine.valuation_engine import (
    ValuationEvidenceState,
    ValuationIdentity,
    build_case1_valuation,
    build_case2_valuation,
)


ROOT = Path(__file__).parents[1]
UTC = timezone.utc
AUDIT_AS_OF = datetime(2026, 9, 6, 12, tzinfo=UTC)


def test_nonpositive_cumulative_cfo_only_unresolves_supporting_capex_ratio():
    history = load_financial_history(ROOT / "data" / "raw" / "STRL.json")
    payload = history.model_dump()
    for period, cfo in zip(payload["periods"][-3:], (-10.0, 5.0, 5.0), strict=True):
        period["cfo"] = cfo
    modified = FinancialHistory.model_validate(payload)

    assert cumulative_capex_to_cfo_3y(modified) is None
    snapshot = build_case1_snapshot(modified, CapitalModel.PROJECT_BASED)
    cash = next(metric for metric in snapshot.metrics if metric.name == "cash_economics")
    assert cash.grade == Grade.X
    assert cash.supporting_tag == "not_meaningful"
    assert "CAPEX/CFO unresolved" in cash.note


def test_case1_rejects_nonconsecutive_annual_observations():
    history = load_financial_history(ROOT / "data" / "raw" / "STRL.json")
    payload = history.model_dump()
    payload["periods"][-1]["fiscal_year"] += 1
    with pytest.raises(ValidationError, match="fiscal_year labels must be consecutive"):
        FinancialHistory.model_validate(payload)


def test_case2_rejects_noncomparable_annual_period_gap():
    periods = (
        Case2AnnualPeriod(fiscal_year=2023, fiscal_period_end=date(2023, 12, 31), revenue=10, gross_profit=5, operating_income=-2, cfo=-2, growth_capex=1, liquidity=10, actual_common_shares=10),
        Case2AnnualPeriod(fiscal_year=2024, fiscal_period_end=date(2024, 12, 31), revenue=12, gross_profit=6, operating_income=-2, cfo=-2, growth_capex=1, liquidity=10, actual_common_shares=10),
        Case2AnnualPeriod(fiscal_year=2025, fiscal_period_end=date(2025, 6, 30), revenue=14, gross_profit=7, operating_income=-1, cfo=-1, growth_capex=1, liquidity=10, actual_common_shares=10),
    )
    with pytest.raises(ValidationError, match="not comparable"):
        Case2QuantInput(
            snapshot_id="bad-periods",
            ticker="TEST",
            periods=periods,
            period_end=periods[-1].fiscal_period_end,
            available_at=AUDIT_AS_OF,
            as_of=AUDIT_AS_OF,
            growth_scope="same_scope",
            core_revenue_representative=True,
            commercial_evidence_exists=True,
        )


@pytest.mark.parametrize("metric_name", sorted(CASE1_CORE_METRICS))
def test_case1_actual_builder_rejects_each_missing_core_metric(metric_name):
    history = load_financial_history(ROOT / "data" / "raw" / "STRL.json")
    built = build_case1_snapshot(history, CapitalModel.PROJECT_BASED)
    with pytest.raises(ValueError, match="frozen Core 8"):
        validate_case1_core_metrics(
            metric for metric in built.metrics if metric.name != metric_name
        )


@pytest.mark.parametrize(
    "metric_name",
    (
        "revenue_growth",
        "gross_profit_growth",
        "cash_burn_trend",
        "runway",
        "dilution",
        "revenue_per_share_growth",
    ),
)
def test_case2_actual_builder_rejects_each_missing_core_metric(metric_name):
    built = load_demo_profile(ROOT, "TEM").analysis.quant
    modified = built.model_copy(
        update={
            "metrics": tuple(
                metric for metric in built.metrics if metric.name != metric_name
            )
        }
    )
    with pytest.raises(ValueError, match="frozen Core 6"):
        validate_case2_quant_snapshot(modified)


def test_core_metric_cannot_be_relabelled_as_supporting():
    case1 = load_demo_profile(ROOT, "STRL").analysis.quant
    changed_case1 = tuple(
        metric.model_copy(update={"is_core": False, "weight": 0})
        if metric.name == "revenue_growth"
        else metric
        for metric in case1.metrics
    )
    with pytest.raises(ValueError, match="relabeled as supporting"):
        validate_case1_core_metrics(changed_case1)

    case2 = load_demo_profile(ROOT, "TEM").analysis.quant
    changed_case2 = case2.model_copy(
        update={
            "metrics": tuple(
                metric.model_copy(update={"is_core": False, "weight": 0})
                if metric.name == "revenue_growth"
                else metric
                for metric in case2.metrics
            )
        }
    )
    with pytest.raises(ValueError, match="frozen Core 6"):
        validate_case2_quant_snapshot(changed_case2)


def test_unresolved_metric_with_grade_is_rejected():
    with pytest.raises(ValidationError, match="unresolved metric"):
        MetricResult(
            name="revenue_growth",
            state=ResolutionState.UNRESOLVED,
            grade=Grade.A,
            weight=1,
        )


def _unknown_current_snapshot(ticker: str = "TEST"):
    return build_case2_current_trend(
        Case2CurrentInput(
            snapshot_id="unknown-current",
            ticker=ticker,
            period_end=date(2026, 6, 30),
            available_at=AUDIT_AS_OF,
            as_of=AUDIT_AS_OF,
            growth_scope="same_scope",
            annual_quant_grade=Grade.B,
            annual_revenue_growth=0.30,
            current_revenue=None,
            prior_comparable_revenue=None,
            current_gross_profit=None,
            prior_comparable_gross_profit=None,
            current_cfo=None,
            current_growth_capex=None,
            prior_comparable_cfo=None,
            prior_comparable_growth_capex=None,
            current_runway_months=None,
            actual_shares_growth=None,
            primary_kpi_states=(DirectionState.UNRESOLVED,),
        )
    )


def test_missing_current_inputs_preserve_unknown_flag_states():
    snapshot = _unknown_current_snapshot()
    states = {item.flag: item.state for item in snapshot.flag_results}
    assert states[TrendFlag.FUNDING_STRESS] == BinaryEvidenceState.UNKNOWN
    assert states[TrendFlag.COMMERCIAL_INFLECTION] == BinaryEvidenceState.UNKNOWN
    assert states[TrendFlag.COMMERCIAL_DETERIORATION] == BinaryEvidenceState.UNKNOWN


def test_unknown_flags_survive_persistence_payload_round_trip():
    profile = load_demo_profile(ROOT, "TEM")
    analysis = profile.analysis.model_copy(
        update={
            "current_trend": _unknown_current_snapshot("TEM"),
            "available_at": AUDIT_AS_OF,
            "as_of": AUDIT_AS_OF,
        }
    )
    rows = analysis_to_rows(
        analysis,
        instrument_id="instrument-tem-audit",
        company_id="company-tem-audit",
        created_at=AUDIT_AS_OF,
    )
    restored = analysis_from_row(rows.root)
    states = {item.flag: item.state for item in restored.current_trend.flag_results}
    assert set(states.values()) == {BinaryEvidenceState.UNKNOWN}


def _case2_valuation_kwargs():
    profile = load_demo_profile(ROOT, "TEM")
    valuation = profile.analysis.valuation
    assert valuation is not None
    assert profile.baseline_price is not None
    assert profile.current_revenue is not None
    assert profile.shares_for_market_cap is not None
    assert profile.valuation_evidence is not None
    return profile, valuation


def test_valuation_rejects_evidence_not_public_at_as_of():
    profile, valuation = _case2_valuation_kwargs()
    identity = ValuationIdentity(
        snapshot_id="future-evidence",
        ticker="TEM",
        period_end=profile.analysis.period_end,
        available_at=profile.analysis.as_of,
        as_of=profile.analysis.as_of,
    )
    future = profile.valuation_evidence.model_copy(
        update={"available_at": profile.analysis.as_of + timedelta(seconds=1)}
    )
    with pytest.raises(ValueError, match="evidence is not available"):
        build_case2_valuation(
            identity=identity,
            assumptions=valuation.assumption_set,
            current_market_cap=valuation.market_cap,
            current_price=profile.baseline_price.price,
            current_revenue=profile.current_revenue,
            current_share_count=profile.shares_for_market_cap,
            required_return=profile.required_return,
            evidence=future,
            asymmetry_type=profile.asymmetry_type,
        )


def test_valuation_rejects_future_exit_multiple_evidence():
    profile, valuation = _case2_valuation_kwargs()
    identity = ValuationIdentity(
        snapshot_id="future-exit-evidence",
        ticker="TEM",
        period_end=profile.analysis.period_end,
        available_at=profile.analysis.as_of,
        as_of=profile.analysis.as_of,
    )
    future_multiples = tuple(
        item.model_copy(update={"as_of": profile.analysis.as_of + timedelta(seconds=1)})
        for item in valuation.assumption_set.exit_multiples
    )
    assumptions = valuation.assumption_set.model_copy(
        update={"exit_multiples": future_multiples}
    )
    with pytest.raises(ValueError, match="exit-multiple evidence"):
        build_case2_valuation(
            identity=identity,
            assumptions=assumptions,
            current_market_cap=valuation.market_cap,
            current_price=profile.baseline_price.price,
            current_revenue=profile.current_revenue,
            current_share_count=profile.shares_for_market_cap,
            required_return=profile.required_return,
            evidence=profile.valuation_evidence,
            asymmetry_type=profile.asymmetry_type,
        )


def _case1_assumptions(as_of: datetime) -> ValuationAssumptionSet:
    return ValuationAssumptionSet(
        assumption_set_id="case1-audit",
        version=1,
        case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
        horizon_years=3,
        terminal_stage=TerminalStage.MATURE,
        terminal_stage_rationale="audit fixture",
        terminal_stage_confidence=ValuationConfidence.MEDIUM,
        primary_metric=ValuationMetric.PE,
        exit_multiples=tuple(
            ExitMultipleAssumption(
                band=band,
                metric_type=ValuationMetric.PE,
                value=value,
                evidence_type=ExitMultipleEvidenceSource.COMPANY_HISTORY,
                source_reference="audit fixture",
                as_of=as_of,
                rationale="audit fixture",
            )
            for band, value in zip(ExitMultipleBand, (10, 15, 20), strict=True)
        ),
        plausible_growth_range=AssumptionRange(low=0.10, high=0.20),
    )


def test_case1_eps_changes_generated_fingerprint_but_price_does_not_enter_it():
    identity = ValuationIdentity(
        snapshot_id="case1-fingerprint",
        ticker="TEST",
        period_end=date(2025, 12, 31),
        available_at=AUDIT_AS_OF,
        as_of=AUDIT_AS_OF,
    )
    evidence = ValuationEvidenceState(
        credible_evidence_count=2,
        company_economics_stable=True,
        company_economics_rapidly_changing=False,
        available_at=AUDIT_AS_OF,
    )
    first = build_case1_valuation(
        identity=identity,
        assumptions=_case1_assumptions(AUDIT_AS_OF),
        current_price=100,
        current_eps=5,
        required_return=0.15,
        evidence=evidence,
        asymmetry_type=AsymmetryType.BALANCED,
    )
    repriced = build_case1_valuation(
        identity=identity.model_copy(update={"snapshot_id": "case1-repriced"}),
        assumptions=first.assumption_set,
        current_price=120,
        current_eps=5,
        required_return=0.15,
        evidence=evidence,
        asymmetry_type=AsymmetryType.BALANCED,
    )
    changed_eps = build_case1_valuation(
        identity=identity.model_copy(update={"snapshot_id": "case1-new-eps"}),
        assumptions=first.assumption_set,
        current_price=100,
        current_eps=6,
        required_return=0.15,
        evidence=evidence,
        asymmetry_type=AsymmetryType.BALANCED,
    )
    assert first.fundamental_input_fingerprint == repriced.fundamental_input_fingerprint
    assert first.fundamental_input_fingerprint != changed_eps.fundamental_input_fingerprint


def _analysis_variant(
    identifier: str,
    *,
    price: float = 60,
    revenue_multiplier: float = 1,
    share_multiplier: float = 1,
    assumption_version: int = 1,
    policy: InvestmentGradePolicyVersion = InvestmentGradePolicyVersion.V1_1,
    remove_fingerprint: bool = False,
) -> AnalysisSnapshot:
    profile = load_demo_profile(ROOT, "TEM")
    base = profile.analysis
    assert base.valuation is not None
    assert base.current_trend is not None
    assert base.narrative is not None
    assert profile.current_revenue is not None
    assert profile.shares_for_market_cap is not None
    assert profile.valuation_evidence is not None
    when = AUDIT_AS_OF + timedelta(days=int(identifier.rsplit("-", 1)[-1]))
    shares = profile.shares_for_market_cap * share_multiplier
    assumptions = base.valuation.assumption_set.model_copy(
        update={"version": assumption_version}
    )
    valuation = build_case2_valuation(
        identity=ValuationIdentity(
            snapshot_id=f"{identifier}-valuation",
            ticker="TEM",
            period_end=base.period_end,
            available_at=when,
            as_of=when,
        ),
        assumptions=assumptions,
        current_market_cap=price * shares / 1000,
        current_price=price,
        current_revenue=profile.current_revenue * revenue_multiplier,
        current_share_count=shares,
        required_return=profile.required_return,
        evidence=profile.valuation_evidence,
        asymmetry_type=profile.asymmetry_type,
    )
    if remove_fingerprint:
        valuation = valuation.model_copy(update={"fundamental_input_fingerprint": None})
    quant = base.quant.model_copy(update={"snapshot_id": f"{identifier}-quant"})
    current = base.current_trend.model_copy(update={"snapshot_id": f"{identifier}-current"})
    narrative = base.narrative.model_copy(update={"snapshot_id": f"{identifier}-narrative"})
    grade_builder = (
        build_investment_grade_v1_1
        if policy == InvestmentGradePolicyVersion.V1_1
        else build_investment_grade
    )
    extra = (
        {"meaningful_optionality": False, "highly_stage_sensitive": False}
        if policy == InvestmentGradePolicyVersion.V1_1
        else {}
    )
    grade = grade_builder(
        snapshot_id=f"{identifier}-grade",
        ticker="TEM",
        period_end=base.period_end,
        available_at=when,
        as_of=when,
        case=base.case,
        quant=quant,
        current_trend=current,
        narrative_gate=base.narrative_gate,
        valuation=valuation,
        thesis_breaker_triggered=False,
        **extra,
    )
    return AnalysisSnapshot(
        snapshot_id=identifier,
        ticker="TEM",
        company_name=base.company_name,
        case=base.case,
        case_definition_version=base.case_definition_version,
        quant=quant,
        current_trend=current,
        narrative=narrative,
        narrative_gate=base.narrative_gate,
        valuation=valuation,
        investment_grade=grade,
        reference_price_snapshot_id=f"{identifier}-price",
        period_end=base.period_end,
        available_at=when,
        as_of=when,
    )


def _persist_restore_and_compare(tmp_path: Path, previous: AnalysisSnapshot, current: AnalysisSnapshot):
    engine = create_sqlite_engine(tmp_path / "audit.sqlite3")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        identities = IdentityRepository(session)
        identities.add_company(
            Company(
                company_id="company-tem-audit",
                canonical_name="Tempus AI audit fixture",
                country="US",
                created_at=AUDIT_AS_OF,
            )
        )
        identities.add_instrument(
            Instrument(
                instrument_id="instrument-tem-audit",
                company_id="company-tem-audit",
                ticker="TEM",
                exchange="NASDAQ",
                currency="USD",
            )
        )
        valuations = ValuationRepository(session)
        assumptions_by_version = {
            item.valuation.assumption_set.version: item.valuation.assumption_set
            for item in (previous, current)
        }
        for assumption in assumptions_by_version.values():
            valuations.add_valuation_assumption(
                assumption,
                valid_from=assumption.exit_multiples[0].as_of,
                created_at=AUDIT_AS_OF,
                instrument_id="instrument-tem-audit",
            )
        analyses = AnalysisRepository(session)
        analyses.add_analysis_snapshot(
            previous,
            instrument_id="instrument-tem-audit",
            company_id="company-tem-audit",
            created_at=previous.as_of,
        )
        analyses.add_analysis_snapshot(
            current,
            instrument_id="instrument-tem-audit",
            company_id="company-tem-audit",
            created_at=current.as_of,
        )
    with factory() as session:
        analyses = AnalysisRepository(session)
        restored_previous = analyses.get_analysis_snapshot(previous.snapshot_id)
        restored_current = analyses.get_analysis_snapshot(current.snapshot_id)
        assert restored_previous is not None and restored_current is not None
        return build_snapshot_diff(restored_previous, restored_current)


@pytest.mark.parametrize(
    ("previous_kwargs", "current_kwargs", "expected"),
    (
        ({}, {"price": 61}, ValuationChangeType.PRICE_ONLY),
        ({}, {"revenue_multiplier": 1.1}, ValuationChangeType.FUNDAMENTAL_CHANGE),
        ({}, {"share_multiplier": 1.1}, ValuationChangeType.FUNDAMENTAL_CHANGE),
        ({}, {"price": 61, "revenue_multiplier": 1.1}, ValuationChangeType.MIXED),
        ({}, {"assumption_version": 2}, ValuationChangeType.ASSUMPTION_CHANGE),
        (
            {"policy": InvestmentGradePolicyVersion.V1},
            {"policy": InvestmentGradePolicyVersion.V1_1},
            ValuationChangeType.POLICY_CHANGE,
        ),
        (
            {"remove_fingerprint": True},
            {"price": 61, "remove_fingerprint": True},
            ValuationChangeType.UNRESOLVED,
        ),
    ),
)
def test_actual_builder_persistence_and_comparison_contract(
    tmp_path,
    previous_kwargs,
    current_kwargs,
    expected,
):
    previous = _analysis_variant("audit-1", **previous_kwargs)
    current = _analysis_variant("audit-2", **current_kwargs)
    diff = _persist_restore_and_compare(tmp_path, previous, current)
    assert diff.valuation_change_type == expected
