"""Deterministic normalized input -> existing Case engines -> immutable storage.

No acquisition, ticker routing rules, scheduler or research fixture lookup lives here.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.case_backtest_adapters import Case1BacktestAdapter, Case1BacktestInput
from engine.case2_current import Case2CurrentInput, build_case2_current_trend
from engine.case2_policy import EligibilityState
from engine.case2_quant import Case2QuantInput, build_case2_quant
from engine.investment_grade_engine_v1_1 import build_investment_grade_v1_1
from engine.models import CaseType
from engine.narrative_engine import derive_gate_from_snapshot
from engine.persistence.models import OnboardingRecordRow, PriceSnapshotRow, ThesisDefinitionRow, TrackingKPIDefinitionRow, ValuationAssumptionRow
from engine.persistence.repositories import AnalysisRepository, IdentityRepository, PriceRepository, ValuationRepository
from engine.persistence.schemas import Company, Instrument, SourceReference
from engine.router import RouterInput, route_case
from engine.tracking_models import (
    AnalysisCase, AnalysisSnapshot, AsymmetryType, CurrentTrendSnapshot,
    FrozenDomainModel, InvestmentGrade, NarrativeSnapshot, PriceBasis, PriceSnapshot,
    PriceType, ResolutionState, ValuationAssumptionSet, validate_valuation_evidence_timing,
)
from engine.valuation_engine import (
    ValuationEvidenceState, ValuationIdentity, build_case1_valuation, build_case2_valuation,
)
from engine.watchlist_registry import MembershipStatus, WatchlistRepository


class InputUsage(str, Enum):
    VALIDATION = "DEMO/VALIDATION"
    APPROVED = "APPROVED"


class RouterFacts(FrozenDomainModel):
    profitable: bool
    recent_operating_loss: bool = False
    structurally_cyclical: bool = False
    high_roic_long_duration: bool = False
    mature_slow_growth: bool = False
    asset_or_event_driven: bool = False


class ValuationInputs(FrozenDomainModel):
    assumptions: ValuationAssumptionSet
    evidence: ValuationEvidenceState
    required_return: float = 0.15
    asymmetry_type: AsymmetryType
    usage: InputUsage
    approval_reference: str = Field(min_length=1)
    # Shares are actual individual shares, monetary totals use financial_unit_scale.
    current_shares: float = Field(gt=0)
    shares_period_end: date
    shares_available_at: datetime
    share_basis_version: str = Field(min_length=1)
    price_share_basis_verified: bool


class TrackingReferences(FrozenDomainModel):
    thesis_id: str
    thesis_version: int = Field(ge=1)
    kpi_definition_ids: tuple[str, ...] = ()


class OnboardingInput(FrozenDomainModel):
    contract_version: Literal["stock-onboarding-v1"] = "stock-onboarding-v1"
    request_id: str = Field(min_length=1, max_length=100)
    company: Company
    instrument: Instrument
    router: RouterFacts
    as_of: datetime
    created_at: datetime
    financial_currency: str = Field(min_length=3, max_length=3)
    financial_unit_scale: Literal[1, 1000, 1000000]
    accounting_scope: Literal["reported_gaap"] = "reported_gaap"
    usage: InputUsage
    sources: tuple[SourceReference, ...] = Field(min_length=1)
    case1: Case1BacktestInput | None = None
    case2: Case2QuantInput | None = None
    case1_current: CurrentTrendSnapshot | None = None
    case2_current: Case2CurrentInput | None = None
    narrative: NarrativeSnapshot | None = None
    commercial_evidence_exists: bool = False
    thesis_breaker_triggered: bool = False
    core_narrative_evidence_damaged: bool = False
    meaningful_optionality: bool = False
    highly_stage_sensitive: bool = False
    valuation: ValuationInputs | None = None
    price: PriceSnapshot | None = None
    price_instrument_id: str | None = None
    price_session_date: date | None = None
    exchange_timezone: str = "UTC"
    tracking: TrackingReferences | None = None

    @model_validator(mode="after")
    def validate_contract(self):
        for value in (self.as_of, self.created_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("onboarding times must be timezone-aware")
        if self.created_at < self.as_of:
            raise ValueError("created_at cannot precede as_of")
        if self.company.company_id != self.instrument.company_id:
            raise ValueError("Company / Instrument identity mismatch")
        if any(not value.strip() for value in (self.company.company_id, self.instrument.instrument_id,
                self.company.canonical_name, self.instrument.ticker, self.instrument.exchange)):
            raise ValueError("stable identity and display fields cannot be empty")
        if self.financial_currency != self.instrument.currency:
            raise ValueError("financial currency must match instrument")
        if any(source.available_at > self.as_of for source in self.sources):
            raise ValueError("source available_at cannot exceed as_of")
        if self.case1 is not None and self.case2 is not None:
            raise ValueError("supply only one Case input")
        components = (self.case1, self.case2, self.case1_current, self.case2_current, self.narrative)
        for part in components:
            if part is None:
                continue
            if part.available_at.tzinfo is None or part.available_at > self.as_of or part.as_of != self.as_of:
                raise ValueError("component availability/as_of mismatch")
            ticker = part.history.ticker if isinstance(part, Case1BacktestInput) else part.ticker
            if ticker != self.instrument.ticker:
                raise ValueError("component ticker mismatch")
            if hasattr(part, "period_end") and part.period_end > self.as_of.date():
                raise ValueError("component period_end cannot exceed as_of")
        if self.case1 is not None:
            if self.financial_unit_scale != 1 or self.case1.history.currency != self.financial_currency:
                raise ValueError("Case 1 FinancialHistory uses base currency units")
            if any(s.filing_date > self.case1.available_at.date()
                   for p in self.case1.history.periods for s in p.sources):
                raise ValueError("financial availability precedes source filing")
        if self.case1_current is not None and (
            self.case1_current.case != AnalysisCase.CASE_1_PROFITABLE_GROWTH
            or self.case1_current.model_version != "case1-current-v1-frozen"
        ):
            raise ValueError("Case 1 Current requires the existing versioned Case 1 overlay")
        if self.price is not None:
            p = self.price
            if (self.price_instrument_id != self.instrument.instrument_id
                    or p.company_id != self.company.company_id or p.ticker != self.instrument.ticker
                    or p.currency != self.instrument.currency):
                raise ValueError("price instrument/currency mismatch")
            if p.price_basis != PriceBasis.RAW or p.price_type != PriceType.CLOSE:
                raise ValueError("onboarding v1 requires RAW close, not adjusted price/EPS mixing")
            if p.timestamp > self.as_of:
                raise ValueError("price timestamp cannot exceed as_of")
            if self.price_session_date != p.timestamp.astimezone(ZoneInfo(self.exchange_timezone)).date():
                raise ValueError("price session date mismatch")
        elif self.price_session_date is not None or self.price_instrument_id is not None:
            raise ValueError("price identity requires a PriceSnapshot")
        if self.valuation is not None:
            v = self.valuation
            if v.shares_available_at.tzinfo is None or v.shares_available_at > self.as_of:
                raise ValueError("shares available_at cannot exceed as_of")
            if v.shares_period_end > v.shares_available_at.date():
                raise ValueError("shares period cannot exceed availability")
            if self.usage == InputUsage.APPROVED and v.usage != InputUsage.APPROVED:
                raise ValueError("validation assumptions cannot be promoted to approved")
            validate_valuation_evidence_timing(
                evaluation_as_of=self.as_of, assumption_set=v.assumptions,
                evidence_available_at=v.evidence.available_at,
                evidence_retrieved_at=v.evidence.retrieved_at,
                require_evidence_available_at=True,
            )
        if self.price is not None:
            information_times = [s.available_at for s in self.sources]
            information_times.extend(p.available_at for p in components if p is not None)
            if self.valuation is not None:
                information_times.extend([self.valuation.shares_available_at, self.valuation.evidence.available_at])
                information_times.extend(e.as_of for e in self.valuation.assumptions.exit_multiples)
            if self.price.timestamp < max(information_times):
                raise ValueError("price precedes required public information; cannot pair old price with later evidence")
        return self


class OnboardingResult(FrozenDomainModel):
    contract_version: Literal["stock-onboarding-v1"] = "stock-onboarding-v1"
    request_id: str
    ticker: str
    instrument_id: str
    identity_status: Literal["COMPLETE"] = "COMPLETE"
    case: str | None
    case_status: Literal["SUPPORTED", "CASE_UNRESOLVED", "BLOCKED_UNIMPLEMENTED_CASE"]
    analysis_snapshot_id: str | None
    analysis_status: Literal["COMPLETE", "BLOCKED"]
    valuation_status: ResolutionState
    investment_grade: InvestmentGrade | None
    watchlist_status: MembershipStatus | None = None
    tracking_kpi_status: Literal["REGISTERED", "NOT_REGISTERED"] = "NOT_REGISTERED"
    unresolved_reasons: tuple[str, ...] = ()


class Case1OnboardingAdapter:
    case = AnalysisCase.CASE_1_PROFITABLE_GROWTH

    def build(self, inputs: OnboardingInput, snapshot_id: str) -> AnalysisSnapshot:
        part = inputs.case1
        if part is None or inputs.case2_current is not None:
            raise ValueError("Case 1 route requires Case 1 inputs")
        adapter = Case1BacktestAdapter()
        if not adapter.is_eligible(part, inputs.as_of):
            raise ValueError("Case 1 financial input is not eligible")
        result = adapter.evaluate(part.model_copy(update={
            "snapshot_id": snapshot_id, "quant_snapshot_id": snapshot_id + "-quant",
        }), inputs.as_of)
        current = inputs.case1_current.model_copy(update={"snapshot_id": snapshot_id + "-current"}) if inputs.case1_current else None
        return result.model_copy(update={"current_trend": current})


class Case2OnboardingAdapter:
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH

    def build(self, inputs: OnboardingInput, snapshot_id: str) -> AnalysisSnapshot:
        part = inputs.case2
        if part is None or inputs.case1_current is not None:
            raise ValueError("Case 2 route requires Case 2 inputs")
        result = build_case2_quant(part.model_copy(update={"snapshot_id": snapshot_id + "-quant"}))
        if result.eligibility != EligibilityState.ELIGIBLE:
            raise ValueError("Case 2 financial input is not eligible")
        current = build_case2_current_trend(inputs.case2_current.model_copy(update={
            "snapshot_id": snapshot_id + "-current", "annual_quant_grade": result.snapshot.grade,
            "annual_revenue_growth": next(m.value for m in result.snapshot.metrics if m.name == "revenue_growth"),
        })) if inputs.case2_current else None
        return AnalysisSnapshot(
            snapshot_id=snapshot_id, ticker=inputs.instrument.ticker,
            company_name=inputs.company.canonical_name, case=self.case,
            case_definition_version="case2-v1-frozen", period_end=part.period_end,
            available_at=part.available_at, as_of=inputs.as_of,
            quant=result.snapshot, current_trend=current,
        )


ADAPTERS = {
    CaseType.PROFITABLE_GROWTH: Case1OnboardingAdapter(),
    CaseType.LOSS_MAKING_GROWTH: Case2OnboardingAdapter(),
}


def build_onboarding_analysis(inputs: OnboardingInput, adapter, snapshot_id: str):
    analysis = adapter.build(inputs, snapshot_id)
    narrative = inputs.narrative.model_copy(update={"snapshot_id": snapshot_id + "-narrative"}) if inputs.narrative else None
    if narrative is not None and narrative.case != analysis.case:
        raise ValueError("Narrative Case mismatch")
    gate = None
    if narrative is not None and analysis.case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH:
        gate = derive_gate_from_snapshot(narrative,
            commercial_evidence_exists=inputs.commercial_evidence_exists,
            thesis_breaker_triggered=inputs.thesis_breaker_triggered,
            core_evidence_damaged=inputs.core_narrative_evidence_damaged).gate
    components = [part for part in (analysis.quant, analysis.current_trend, narrative) if part is not None]
    available_at = max([part.available_at for part in components] + [s.available_at for s in inputs.sources])
    period_end = max(part.period_end for part in components)
    v, price = inputs.valuation, inputs.price
    if price is not None:
        available_at = max(available_at, price.timestamp)
    reasons = []
    valuation = None
    if v is None:
        reasons.append("VALUATION_ASSUMPTIONS_UNAVAILABLE")
    elif v.assumptions.case != analysis.case:
        raise ValueError("Valuation assumption Case mismatch")
    elif price is None:
        reasons.append("PRICE_UNAVAILABLE")
    elif not v.price_share_basis_verified:
        reasons.append("SHARE_SPLIT_BASIS_UNRESOLVED")
    else:
        available_at = max(available_at, price.timestamp, v.shares_available_at, v.evidence.available_at,
                           *(e.as_of for e in v.assumptions.exit_multiples))
        kwargs = dict(identity=ValuationIdentity(snapshot_id=snapshot_id + "-valuation",
            ticker=inputs.instrument.ticker, period_end=period_end, available_at=available_at, as_of=inputs.as_of),
            assumptions=v.assumptions, current_price=price.price, required_return=v.required_return,
            evidence=v.evidence, asymmetry_type=v.asymmetry_type)
        if analysis.case == AnalysisCase.CASE_1_PROFITABLE_GROWTH:
            eps = inputs.case1.history.periods[-1].diluted_eps
            if eps > 0:
                valuation = build_case1_valuation(**kwargs, current_eps=eps)
            else:
                reasons.append("VALUATION_EPS_UNRESOLVED")
        else:
            valuation = build_case2_valuation(**kwargs,
                current_market_cap=price.price * v.current_shares / inputs.financial_unit_scale,
                current_share_count=v.current_shares, current_revenue=inputs.case2.periods[-1].revenue)
    ig = build_investment_grade_v1_1(
        snapshot_id=snapshot_id + "-ig", ticker=inputs.instrument.ticker,
        period_end=period_end, available_at=available_at, as_of=inputs.as_of, case=analysis.case,
        quant=analysis.quant, current_trend=analysis.current_trend, narrative_gate=gate,
        valuation=valuation, thesis_breaker_triggered=inputs.thesis_breaker_triggered,
        meaningful_optionality=inputs.meaningful_optionality, highly_stage_sensitive=inputs.highly_stage_sensitive,
    )
    if ig.final_grade == InvestmentGrade.U and ig.rationale:
        reasons.append(ig.rationale)
    analysis = AnalysisSnapshot.model_validate({**analysis.model_dump(),
        "period_end": period_end, "available_at": available_at, "narrative": narrative,
        "narrative_gate": gate, "valuation": valuation, "investment_grade": ig,
        "reference_price_snapshot_id": price.price_snapshot_id if price else None,
    })
    return analysis, tuple(dict.fromkeys(reasons))


class StockOnboardingService:
    def __init__(self, session: Session):
        self.session = session

    def analyze(self, inputs: OnboardingInput, *, track: bool = False) -> OnboardingResult:
        if self.session.new or self.session.dirty or self.session.deleted:
            raise ValueError("onboarding requires a session without pending writes")
        # Existing repositories commit individually. Their commits join this outer
        # transaction without committing it: identities, history and receipt are atomic.
        try:
            with Session(bind=self.session.connection(), join_transaction_mode="rollback_only") as unit:
                result = StockOnboardingService(unit)._analyze(inputs, track=track)
            self.session.commit()
            self.session.expire_all()
            return result
        except Exception:
            # A repository rollback may already have ended the joined transaction.
            # close() resets this reusable Session without rolling it back twice.
            self.session.close()
            raise

    def _analyze(self, inputs: OnboardingInput, *, track: bool) -> OnboardingResult:
        # Revalidate even model_copy / model_construct inputs; no trusted bypass.
        inputs = OnboardingInput.model_validate(inputs.model_dump(mode="json"))
        canonical = inputs.model_dump(mode="json")
        fingerprint = sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        existing = self.session.get(OnboardingRecordRow, inputs.request_id)
        if existing:
            if existing.input_fingerprint != fingerprint:
                raise ValueError("request_id already exists with different input; create a new request")
            result = OnboardingResult.model_validate(existing.payload["result"])
        else:
            route = route_case(RouterInput(**inputs.router.model_dump()))
            adapter = ADAPTERS.get(route)
            snapshot_id = "onboard-" + sha256(inputs.request_id.encode()).hexdigest()
            analysis, reasons = build_onboarding_analysis(inputs, adapter, snapshot_id) if adapter else (None, ())
            case_status = "SUPPORTED" if adapter else "CASE_UNRESOLVED" if route is None else "BLOCKED_UNIMPLEMENTED_CASE"
            if adapter is None:
                reasons = (case_status,)
            self._validate_tracking(inputs)
            identities = IdentityRepository(self.session)
            for old, new in ((identities.get_company(inputs.company.company_id), inputs.company),
                             (identities.get_instrument(inputs.instrument.instrument_id), inputs.instrument)):
                if old is not None and old != new:
                    raise ValueError("stable identity exists with different content")
            if identities.get_company(inputs.company.company_id) is None:
                identities.add_company(inputs.company)
            if identities.get_instrument(inputs.instrument.instrument_id) is None:
                identities.add_instrument(inputs.instrument)
            if inputs.valuation is not None:
                assumptions = inputs.valuation.assumptions
                repo = ValuationRepository(self.session)
                old = repo.get_valuation_assumption(assumptions.assumption_set_id, assumptions.version)
                if old is not None:
                    row = self.session.scalar(select(ValuationAssumptionRow).where(
                        ValuationAssumptionRow.assumption_set_id == assumptions.assumption_set_id,
                        ValuationAssumptionRow.assumption_version == assumptions.version))
                    if old != assumptions or row.instrument_id != inputs.instrument.instrument_id:
                        raise ValueError("assumption version/content/instrument conflict")
                else:
                    repo.add_valuation_assumption(assumptions, valid_from=inputs.as_of,
                        created_at=inputs.created_at, company_id=inputs.company.company_id,
                        instrument_id=inputs.instrument.instrument_id)
            if analysis is not None:
                if inputs.price is not None:
                    prices = PriceRepository(self.session)
                    old_price = prices.get_price_snapshot(inputs.price.price_snapshot_id)
                    old_price_row = self.session.get(PriceSnapshotRow, inputs.price.price_snapshot_id)
                    if old_price is not None and (old_price != inputs.price
                            or old_price_row.instrument_id != inputs.instrument.instrument_id):
                        raise ValueError("price_snapshot_id already exists with different content")
                    if old_price is None:
                        prices.add_price_snapshot(inputs.price, instrument_id=inputs.instrument.instrument_id)
                analyses = AnalysisRepository(self.session)
                old_analysis = analyses.get_analysis_snapshot(analysis.snapshot_id)
                if old_analysis is not None and old_analysis != analysis:
                    raise ValueError("immutable analysis identity conflict")
                if old_analysis is None:
                    analyses.add_analysis_snapshot(analysis, instrument_id=inputs.instrument.instrument_id,
                        company_id=inputs.company.company_id, created_at=inputs.created_at)
            result = OnboardingResult(request_id=inputs.request_id, ticker=inputs.instrument.ticker,
                instrument_id=inputs.instrument.instrument_id, case=route.value if route else None,
                case_status=case_status, analysis_snapshot_id=analysis.snapshot_id if analysis else None,
                analysis_status="COMPLETE" if analysis else "BLOCKED",
                valuation_status=analysis.valuation.state if analysis and analysis.valuation else ResolutionState.UNRESOLVED,
                investment_grade=analysis.investment_grade.final_grade if analysis else None,
                tracking_kpi_status="REGISTERED" if inputs.tracking else "NOT_REGISTERED", unresolved_reasons=reasons)
            self.session.add(OnboardingRecordRow(request_id=inputs.request_id,
                instrument_id=inputs.instrument.instrument_id, analysis_snapshot_id=result.analysis_snapshot_id,
                input_fingerprint=fingerprint, payload={"input": canonical, "result": result.model_dump(mode="json")}))
            self.session.commit()
        registry = WatchlistRepository(self.session)
        membership = registry.add(inputs.instrument.instrument_id, at=inputs.created_at,
            reference_analysis_snapshot_id=result.analysis_snapshot_id, registration_source="stock-onboarding-v1") if track else registry.get(inputs.instrument.instrument_id)
        return result.model_copy(update={"watchlist_status": membership.status if membership else None})

    def _validate_tracking(self, inputs: OnboardingInput) -> None:
        if inputs.tracking is None:
            return
        ref = inputs.tracking
        thesis = self.session.scalar(select(ThesisDefinitionRow).where(
            ThesisDefinitionRow.thesis_id == ref.thesis_id,
            ThesisDefinitionRow.thesis_version == ref.thesis_version))
        if (thesis is None or thesis.valid_from > inputs.as_of
                or (thesis.instrument_id != inputs.instrument.instrument_id
                    and not (thesis.instrument_id is None and thesis.company_id == inputs.company.company_id))):
            raise ValueError("tracking requires an existing comparable thesis version")
        for key in ref.kpi_definition_ids:
            kpi = self.session.scalar(select(TrackingKPIDefinitionRow).where(
                TrackingKPIDefinitionRow.kpi_definition_id == key,
                TrackingKPIDefinitionRow.kpi_set_version == thesis.kpi_set_version))
            if (kpi is None or kpi.thesis_id != ref.thesis_id or kpi.thesis_version != ref.thesis_version
                    or key not in thesis.payload["kpi_definition_ids"]):
                raise ValueError("tracking KPI must belong to registered thesis version")
