"""Small DEMO/VALIDATION operating connection for STRL, TEM, and LPTH.

The service composes existing calculation and persistence boundaries.  It does not add
an investment rule or disguise a price-only evaluation as a new fundamental analysis.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timezone
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Self
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator
from sqlalchemy.orm import Session

from engine.case2_analysis import Case2AnalysisInput, build_case2_analysis
from engine.case2_current import Case2CurrentInput
from engine.case2_policy import actual_share_growth, case2_fcf, runway_months
from engine.case2_quant import Case2AnnualPeriod, Case2QuantInput, build_case2_quant
from engine.case_backtest_adapters import (
    Case1BacktestAdapter,
    Case1BacktestInput,
    evaluate_with_adapter,
)
from engine.financials import load_financial_history
from engine.investment_grade_engine import build_investment_grade
from engine.investment_grade_engine_v1_1 import (
    MODEL_VERSION as INVESTMENT_GRADE_V1_1_MODEL_VERSION,
    VALUATION_UNRESOLVED,
    build_investment_grade_v1_1,
)
from engine.models import CapitalModel
from engine.persistence.models import Base
from engine.persistence.repositories import (
    AnalysisRepository,
    IdentityRepository,
    PriceRepository,
    ValuationRepository,
)
from engine.persistence.schemas import Company, Instrument
from engine.persistence.session import create_session_factory, create_sqlite_engine
from engine.price_tracking import compare_prices
from engine.research_data.contracts import HistoricalSecurityCandidate
from engine.research_data.tiingo import (
    TiingoAdjustmentEvidence,
    TiingoClient,
    TiingoHistoricalPriceSource,
    tiingo_to_price_snapshots,
)
from engine.tracking_models import (
    AdjustmentType,
    AnalysisCase,
    AnalysisSnapshot,
    AsymmetryType,
    AssumptionRange,
    DirectionState,
    ExitMultipleAssumption,
    ExitMultipleBand,
    ExitMultipleEvidenceSource,
    FrozenDomainModel,
    GrowthScope,
    InvestmentGrade,
    InvestmentGradeAdjustment,
    InvestmentGradePolicyVersion,
    InvestmentGradeSnapshot,
    InvestmentGradeTrigger,
    NarrativeAssessment,
    NarrativeSnapshot,
    NarrativeState,
    PriceBasis,
    PriceSnapshot,
    PriceType,
    ResolutionState,
    TerminalStage,
    ValuationAssumptionSet,
    ValuationConfidence,
    ValuationMetric,
    ValuationSnapshot,
)
from engine.valuation_engine import (
    ValuationEvidenceState,
    ValuationIdentity,
    build_case2_valuation,
)


SUPPORTED_TICKERS = ("STRL", "TEM", "LPTH")
US_MARKET_TIMEZONE = ZoneInfo("America/New_York")
DEFAULT_LOCAL_ROOT = Path("data/local/limited-operating")
DEFAULT_DB_PATH = DEFAULT_LOCAL_ROOT / "demo.sqlite3"
DEFAULT_ARTIFACT_PATH = DEFAULT_LOCAL_ROOT / "evaluations.jsonl"


class UsageMode(str, Enum):
    DEMO_VALIDATION = "DEMO/VALIDATION"


class WriteStatus(str, Enum):
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"


class RefreshStatus(str, Enum):
    STORED = "stored"
    ALREADY_EXISTS = "already_exists"
    PENDING_CREDENTIAL = "pending_credential"
    UNAVAILABLE = "unavailable"


class EvaluationChangeType(str, Enum):
    PRICE_ONLY = "PRICE_ONLY"
    POLICY_CHANGE = "POLICY_CHANGE"
    ASSUMPTION_OR_EVIDENCE_CHANGE = "ASSUMPTION_OR_EVIDENCE_CHANGE"
    NONE = "NONE"


class DemoProfile(FrozenDomainModel):
    ticker: str
    company_id: str
    instrument_id: str
    exchange: str
    currency: str = Field(min_length=3, max_length=3)
    country: str
    analysis: AnalysisSnapshot
    baseline_price: PriceSnapshot | None = None
    current_revenue: float | None = None
    shares_for_market_cap: float | None = Field(default=None, gt=0)
    reported_shares_as_of: datetime | None = None
    share_basis_confirmed: bool = False
    required_return: float | None = None
    valuation_evidence: ValuationEvidenceState | None = None
    asymmetry_type: AsymmetryType | None = None
    thesis_breaker_triggered: bool = False
    meaningful_optionality: bool = False
    highly_stage_sensitive: bool = False
    financial_period_label: str
    fundamental_input_reference: str
    fundamental_input_fingerprint: str

    @model_validator(mode="after")
    def validate_profile(self) -> Self:
        if self.analysis.ticker != self.ticker:
            raise ValueError("profile analysis ticker mismatch")
        if self.baseline_price is not None:
            if self.baseline_price.ticker != self.ticker:
                raise ValueError("profile baseline price ticker mismatch")
            if self.baseline_price.currency != self.currency:
                raise ValueError("profile baseline price currency mismatch")
        if self.reported_shares_as_of is not None and (
            self.reported_shares_as_of.tzinfo is None
            or self.reported_shares_as_of.utcoffset() is None
        ):
            raise ValueError("reported_shares_as_of must be timezone-aware")
        return self


class SeedItemResult(FrozenDomainModel):
    ticker: str
    company_id: str
    instrument_id: str
    analysis_snapshot_id: str
    company_status: WriteStatus
    instrument_status: WriteStatus
    analysis_status: WriteStatus
    assumption_status: WriteStatus | None = None
    baseline_price_status: WriteStatus | None = None
    usage_mode: UsageMode = UsageMode.DEMO_VALIDATION


class PriceRefreshResult(FrozenDomainModel):
    ticker: str
    session_date: date
    status: RefreshStatus
    price_snapshot_id: str | None = None
    observation_count: int = Field(default=0, ge=0)
    reason: str | None = None


class OperatingEvaluation(FrozenDomainModel):
    schema_version: str = "limited-operating-evaluation-v0.1"
    evaluation_id: str
    reference_analysis_snapshot_id: str
    instrument_id: str
    ticker: str
    case: AnalysisCase
    price_snapshot_id: str
    price_session_date: date
    price_timestamp: datetime
    price_basis: PriceBasis
    price: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    assumption_set_id: str | None = None
    assumption_version: int | None = Field(default=None, ge=1)
    fundamental_input_reference: str
    fundamental_input_fingerprint: str
    investment_grade_policy_version: InvestmentGradePolicyVersion
    assessment_as_of: datetime
    usage_mode: UsageMode = UsageMode.DEMO_VALIDATION
    financial_period_label: str
    financial_available_at: datetime
    original_analysis_as_of: datetime
    reported_shares_as_of: datetime | None = None
    shares_for_market_cap: float | None = Field(default=None, gt=0)
    estimated_market_cap: float | None = Field(default=None, gt=0)
    valuation_result: ValuationSnapshot | None = None
    investment_grade_result: InvestmentGradeSnapshot
    unresolved_reasons: tuple[str, ...] = ()
    created_at: datetime

    @model_validator(mode="after")
    def validate_evaluation(self) -> Self:
        for name, value in (
            ("price_timestamp", self.price_timestamp),
            ("assessment_as_of", self.assessment_as_of),
            ("financial_available_at", self.financial_available_at),
            ("original_analysis_as_of", self.original_analysis_as_of),
            ("created_at", self.created_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.reported_shares_as_of is not None and (
            self.reported_shares_as_of.tzinfo is None
            or self.reported_shares_as_of.utcoffset() is None
        ):
            raise ValueError("reported_shares_as_of must be timezone-aware")
        if self.financial_available_at > self.original_analysis_as_of:
            raise ValueError("financial information cannot postdate original analysis")
        if self.original_analysis_as_of > self.assessment_as_of:
            raise ValueError("price-only assessment cannot precede original analysis")
        if self.price_timestamp > self.assessment_as_of:
            raise ValueError("price information cannot postdate assessment_as_of")
        if self.created_at < self.assessment_as_of:
            raise ValueError("created_at cannot precede assessment_as_of")
        if self.valuation_result is not None:
            identity = self.valuation_result.assumption_set
            if (
                identity.assumption_set_id != self.assumption_set_id
                or identity.version != self.assumption_version
            ):
                raise ValueError("valuation assumption identity mismatch")
        if self.investment_grade_result.final_grade == InvestmentGrade.U:
            if not self.unresolved_reasons:
                raise ValueError("U evaluation requires an unresolved reason")
        elif self.unresolved_reasons:
            raise ValueError("resolved grade cannot carry unresolved reasons")
        expected_model = (
            INVESTMENT_GRADE_V1_1_MODEL_VERSION
            if self.investment_grade_policy_version == InvestmentGradePolicyVersion.V1_1
            else "investment-grade-v1-frozen"
        )
        if self.investment_grade_result.model_version != expected_model:
            raise ValueError("Investment Grade model version does not match selected policy")
        return self


class OperatingEvaluationDiff(FrozenDomainModel):
    ticker: str
    previous_evaluation_id: str
    current_evaluation_id: str
    change_type: EvaluationChangeType
    previous_price: float
    current_price: float
    price_return: float
    previous_expectation_gap: str
    current_expectation_gap: str
    previous_grade: InvestmentGrade
    current_grade: InvestmentGrade
    assumption_identity_unchanged: bool
    policy_version_unchanged: bool
    fundamental_input_unchanged: bool
    unresolved_reasons: tuple[str, ...] = ()


class EvaluationArtifactStore:
    """Append-only JSONL persistence for derived price-only evaluations."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _items(self) -> tuple[OperatingEvaluation, ...]:
        if not self.path.exists():
            return ()
        items: list[OperatingEvaluation] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                items.append(OperatingEvaluation.model_validate_json(line))
        return tuple(items)

    def get(self, evaluation_id: str) -> OperatingEvaluation | None:
        return next(
            (item for item in self._items() if item.evaluation_id == evaluation_id),
            None,
        )

    def list_for_ticker(self, ticker: str) -> tuple[OperatingEvaluation, ...]:
        return tuple(
            sorted(
                (item for item in self._items() if item.ticker == ticker),
                key=lambda item: (item.assessment_as_of, item.created_at, item.evaluation_id),
            )
        )

    def append(self, evaluation: OperatingEvaluation) -> WriteStatus:
        existing = self.get(evaluation.evaluation_id)
        if existing is not None:
            if existing != evaluation:
                raise ValueError("evaluation_id already exists with different content")
            return WriteStatus.ALREADY_EXISTS
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            evaluation.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(payload + "\n")
        return WriteStatus.CREATED


def _canonical_fingerprint(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _case2_profile(repo_root: Path, ticker: str) -> DemoProfile:
    fixture_path = repo_root / "tests" / "fixtures" / "case2_real_world" / f"{ticker}.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    as_of = datetime.fromisoformat(data["analysis_as_of"])
    annual = data["annual"]
    current = data["current"]
    annual_source = data["sources"][annual["source_id"]]
    current_source = data["sources"][current["source_id"]]
    price_source = data["sources"][data["market"]["source_id"]]
    periods = tuple(Case2AnnualPeriod(**item) for item in annual["periods"])
    quant_input = Case2QuantInput(
        snapshot_id=f"{ticker}-golden-quant",
        ticker=ticker,
        periods=periods,
        period_end=date.fromisoformat(annual["period_end"]),
        available_at=datetime.fromisoformat(annual_source["available_at"]),
        as_of=as_of,
        growth_scope=GrowthScope(annual["growth_scope"]),
        core_revenue_representative=annual["core_revenue_representative"],
        commercial_evidence_exists=annual["commercial_evidence_exists"],
        share_comparison_valid=annual["share_comparison_valid"],
        potential_dilution="see source fixture",
    )
    quant_result = build_case2_quant(quant_input)
    metrics = {item.name: item for item in quant_result.snapshot.metrics}
    latest = periods[-1]
    latest_fcf = (
        case2_fcf(latest.cfo, latest.growth_capex)
        if latest.cfo is not None and latest.growth_capex is not None
        else None
    )
    current_runway = runway_months(current["current_liquidity"], latest_fcf)
    shares_growth = actual_share_growth(
        current["current_actual_shares"], current["prior_actual_shares"]
    )
    axes = data["narrative"]["axes"]
    narrative = NarrativeSnapshot(
        snapshot_id=f"{ticker}-golden-narrative",
        ticker=ticker,
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        model_version="case2-narrative-v1-frozen",
        thesis_id=f"{ticker}-validation-thesis",
        thesis_version=data["narrative"]["thesis_version"],
        kpi_set_version=data["narrative"]["kpi_set_version"],
        kpi_definition_ids=tuple(
            f"{ticker}-kpi-{index}"
            for index, _ in enumerate(current["primary_kpi_states"], 1)
        ),
        assessments=tuple(
            NarrativeAssessment(
                dimension=name,
                state=NarrativeState(value),
                evidence=(data["sources"][data["narrative"]["source_id"]]["url"],),
            )
            for name, value in axes.items()
        ),
        overall=NarrativeState.EMERGING,
        period_end=date.fromisoformat(current["period_end"]),
        available_at=datetime.fromisoformat(current_source["available_at"]),
        as_of=as_of,
    )
    valuation_data = data["valuation"]
    metric = ValuationMetric(valuation_data["primary_metric"])
    assumptions = ValuationAssumptionSet(
        assumption_set_id=valuation_data["assumption_set_id"],
        version=1,
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        horizon_years=valuation_data["horizon_years"],
        terminal_stage=TerminalStage(valuation_data["terminal_stage"]),
        terminal_stage_rationale=valuation_data["rationale"],
        terminal_stage_confidence=ValuationConfidence(
            valuation_data["terminal_stage_confidence"]
        ),
        primary_metric=metric,
        exit_multiples=tuple(
            ExitMultipleAssumption(
                band=band,
                metric_type=metric,
                value=value,
                evidence_type=ExitMultipleEvidenceSource.COMPARABLE_COMPANIES,
                source_reference="validation-only range; see fixture rationale",
                as_of=as_of,
                rationale=valuation_data["rationale"],
            )
            for band, value in zip(
                ExitMultipleBand, valuation_data["exit_multiples"], strict=True
            )
        ),
        plausible_growth_range=AssumptionRange(
            low=valuation_data["plausible_growth_range"][0],
            high=valuation_data["plausible_growth_range"][1],
        ),
        expected_annual_dilution=valuation_data["expected_annual_dilution"],
        terminal_net_debt=valuation_data["terminal_net_debt"],
        notes=("DEMO/VALIDATION; not frozen company fair value",),
    )
    evidence = ValuationEvidenceState(
        credible_evidence_count=valuation_data["credible_evidence_count"],
        company_economics_stable=valuation_data["economics_stable"],
        company_economics_rapidly_changing=valuation_data[
            "economics_rapidly_changing"
        ],
    )
    price_id = f"{ticker}-validation-raw-2026-09-01"
    fingerprint = _canonical_fingerprint(fixture_path)
    analysis_input = Case2AnalysisInput(
        snapshot_id=f"{ticker}-golden-analysis-2026-09-01",
        investment_grade_snapshot_id=f"{ticker}-golden-ig-2026-09-01",
        company_name=data["company_name"],
        period_end=date.fromisoformat(current["period_end"]),
        available_at=as_of,
        as_of=as_of,
        quant=quant_input,
        narrative=narrative,
        commercial_evidence_exists=data["narrative"]["commercial_evidence_exists"],
        thesis_breaker_triggered=data["narrative"]["thesis_breaker_triggered"],
        current=Case2CurrentInput(
            snapshot_id=f"{ticker}-golden-current",
            ticker=ticker,
            period_end=date.fromisoformat(current["period_end"]),
            available_at=datetime.fromisoformat(current_source["available_at"]),
            as_of=as_of,
            growth_scope=GrowthScope(current["growth_scope"]),
            annual_quant_grade=None,
            annual_revenue_growth=metrics["revenue_growth"].value,
            current_revenue=current["current_revenue"],
            prior_comparable_revenue=current["prior_revenue"],
            current_gross_profit=current["current_gross_profit"],
            prior_comparable_gross_profit=current["prior_gross_profit"],
            current_cfo=current["current_cfo"],
            current_growth_capex=current["current_growth_capex"],
            prior_comparable_cfo=current["prior_cfo"],
            prior_comparable_growth_capex=current["prior_growth_capex"],
            current_runway_months=current_runway,
            actual_shares_growth=shares_growth,
            primary_kpi_states=tuple(
                DirectionState(value) for value in current["primary_kpi_states"]
            ),
            thesis_breaker_triggered=data["narrative"]["thesis_breaker_triggered"],
        ),
        valuation_assumptions=assumptions,
        current_market_cap=(
            data["market"]["close"] * data["market"]["shares_for_market_cap"] / 1000
        ),
        current_revenue=latest.revenue,
        required_return=valuation_data["required_return"],
        valuation_evidence=evidence,
        asymmetry_type=AsymmetryType(valuation_data["asymmetry_type"]),
        reference_price_snapshot_id=price_id,
    )
    analysis = build_case2_analysis(analysis_input)
    assert analysis.valuation is not None
    analysis = analysis.model_copy(
        update={
            "valuation": analysis.valuation.model_copy(
                update={"fundamental_input_fingerprint": fingerprint}
            )
        }
    )
    baseline_price = PriceSnapshot(
        price_snapshot_id=price_id,
        ticker=ticker,
        company_id=f"company-{ticker.lower()}",
        timestamp=as_of,
        price=data["market"]["close"],
        currency="USD",
        market_cap=data["market"]["close"]
        * data["market"]["shares_for_market_cap"]
        / 1000,
        source=price_source["source"],
        price_type=PriceType.CLOSE,
        price_basis=PriceBasis.RAW,
        provider_reference=price_source["url"],
        created_at=as_of,
    )
    return DemoProfile(
        ticker=ticker,
        company_id=f"company-{ticker.lower()}",
        instrument_id=f"instrument-{ticker.lower()}-nasdaq",
        exchange="NASDAQ",
        currency="USD",
        country="US",
        analysis=analysis,
        baseline_price=baseline_price,
        current_revenue=latest.revenue,
        shares_for_market_cap=data["market"]["shares_for_market_cap"],
        reported_shares_as_of=datetime.fromisoformat(current_source["available_at"]),
        share_basis_confirmed=True,
        required_return=valuation_data["required_return"],
        valuation_evidence=evidence,
        asymmetry_type=AsymmetryType(valuation_data["asymmetry_type"]),
        thesis_breaker_triggered=data["narrative"]["thesis_breaker_triggered"],
        financial_period_label=(
            f"FY{periods[0].fiscal_year}-FY{periods[-1].fiscal_year}; "
            f"current through {current['period_end']}"
        ),
        fundamental_input_reference=fixture_path.relative_to(repo_root).as_posix(),
        fundamental_input_fingerprint=fingerprint,
    )


def _strl_profile(repo_root: Path) -> DemoProfile:
    fixture_path = repo_root / "data" / "raw" / "STRL.json"
    history = load_financial_history(fixture_path)
    retrieved_at = max(
        source.retrieved_at for period in history.periods for source in period.sources
    )
    inputs = Case1BacktestInput(
        snapshot_id="STRL-demo-analysis-2026-08-30",
        quant_snapshot_id="STRL-demo-quant-2026-08-30",
        history=history,
        capital_model=CapitalModel.PROJECT_BASED,
        available_at=retrieved_at,
        as_of=retrieved_at,
    )
    analysis = evaluate_with_adapter(
        Case1BacktestAdapter(), inputs, as_of=retrieved_at
    )
    return DemoProfile(
        ticker="STRL",
        company_id="company-strl",
        instrument_id="instrument-strl-nasdaq",
        exchange="NASDAQ",
        currency="USD",
        country="US",
        analysis=analysis,
        financial_period_label=(
            f"FY{history.periods[0].fiscal_year}-FY{history.periods[-1].fiscal_year}"
        ),
        fundamental_input_reference=fixture_path.relative_to(repo_root).as_posix(),
        fundamental_input_fingerprint=_canonical_fingerprint(fixture_path),
    )


def load_demo_profile(repo_root: str | Path, ticker: str) -> DemoProfile:
    root = Path(repo_root)
    normalized = ticker.upper()
    if normalized == "STRL":
        return _strl_profile(root)
    if normalized in {"TEM", "LPTH"}:
        return _case2_profile(root, normalized)
    raise ValueError(f"unsupported limited-operating ticker: {ticker}")


def _same_or_error(existing: object, expected: object, label: str) -> WriteStatus:
    if existing != expected:
        raise ValueError(f"existing {label} differs from DEMO/VALIDATION seed")
    return WriteStatus.ALREADY_EXISTS


def _evaluation_id(
    reference_analysis_snapshot_id: str,
    price_snapshot_id: str,
    policy_version: InvestmentGradePolicyVersion,
) -> str:
    raw = f"{reference_analysis_snapshot_id}|{price_snapshot_id}|{policy_version.value}"
    return f"evaluation-{sha256(raw.encode('utf-8')).hexdigest()[:24]}"


class LimitedOperatingService:
    def __init__(
        self,
        session: Session,
        *,
        repo_root: str | Path,
        artifact_path: str | Path,
    ):
        self.session = session
        self.repo_root = Path(repo_root)
        self.artifacts = EvaluationArtifactStore(artifact_path)

    def profile(self, ticker: str) -> DemoProfile:
        return load_demo_profile(self.repo_root, ticker)

    def seed_demo(self, tickers: Iterable[str] = SUPPORTED_TICKERS) -> tuple[SeedItemResult, ...]:
        results: list[SeedItemResult] = []
        for ticker in tickers:
            profile = self.profile(ticker)
            identities = IdentityRepository(self.session)
            company = Company(
                company_id=profile.company_id,
                canonical_name=profile.analysis.company_name,
                country=profile.country,
                created_at=profile.analysis.as_of,
            )
            existing_company = identities.get_company(profile.company_id)
            company_status = (
                _same_or_error(existing_company, company, "company")
                if existing_company is not None
                else WriteStatus.CREATED
            )
            if existing_company is None:
                identities.add_company(company)

            instrument = Instrument(
                instrument_id=profile.instrument_id,
                company_id=profile.company_id,
                ticker=profile.ticker,
                exchange=profile.exchange,
                currency=profile.currency,
            )
            existing_instrument = identities.get_instrument(profile.instrument_id)
            instrument_status = (
                _same_or_error(existing_instrument, instrument, "instrument")
                if existing_instrument is not None
                else WriteStatus.CREATED
            )
            if existing_instrument is None:
                identities.add_instrument(instrument)

            baseline_status: WriteStatus | None = None
            if profile.baseline_price is not None:
                prices = PriceRepository(self.session)
                existing_price = prices.get_price_snapshot(
                    profile.baseline_price.price_snapshot_id
                )
                baseline_status = (
                    _same_or_error(existing_price, profile.baseline_price, "baseline price")
                    if existing_price is not None
                    else WriteStatus.CREATED
                )
                if existing_price is None:
                    prices.add_price_snapshot(
                        profile.baseline_price, instrument_id=profile.instrument_id
                    )

            assumption_status: WriteStatus | None = None
            if profile.analysis.valuation is not None:
                assumptions = profile.analysis.valuation.assumption_set
                valuation_repo = ValuationRepository(self.session)
                existing_assumption = valuation_repo.get_valuation_assumption(
                    assumptions.assumption_set_id, assumptions.version
                )
                assumption_status = (
                    _same_or_error(existing_assumption, assumptions, "valuation assumption")
                    if existing_assumption is not None
                    else WriteStatus.CREATED
                )
                if existing_assumption is None:
                    valuation_repo.add_valuation_assumption(
                        assumptions,
                        instrument_id=profile.instrument_id,
                        valid_from=profile.analysis.available_at,
                        created_at=profile.analysis.as_of,
                    )

            analyses = AnalysisRepository(self.session)
            existing_analysis = analyses.get_analysis_snapshot(
                profile.analysis.snapshot_id
            )
            analysis_status = (
                _same_or_error(existing_analysis, profile.analysis, "analysis")
                if existing_analysis is not None
                else WriteStatus.CREATED
            )
            if existing_analysis is None:
                analyses.add_analysis_snapshot(
                    profile.analysis,
                    instrument_id=profile.instrument_id,
                    company_id=profile.company_id,
                    created_at=profile.analysis.as_of,
                )
            results.append(
                SeedItemResult(
                    ticker=profile.ticker,
                    company_id=profile.company_id,
                    instrument_id=profile.instrument_id,
                    analysis_snapshot_id=profile.analysis.snapshot_id,
                    company_status=company_status,
                    instrument_status=instrument_status,
                    analysis_status=analysis_status,
                    assumption_status=assumption_status,
                    baseline_price_status=baseline_status,
                )
            )
        return tuple(results)

    def store_raw_close(
        self,
        ticker: str,
        session_date: date,
        price: PriceSnapshot,
    ) -> PriceRefreshResult:
        profile = self.profile(ticker)
        if price.ticker != profile.ticker:
            raise ValueError("price ticker does not match requested instrument")
        if price.currency != profile.currency:
            raise ValueError("price currency does not match instrument currency")
        if price.price_basis != PriceBasis.RAW:
            raise ValueError("valuation requires a RAW close")
        observed_session = price.timestamp.astimezone(US_MARKET_TIMEZONE).date()
        if observed_session != session_date:
            raise ValueError("price timestamp does not match requested session_date")
        repo = PriceRepository(self.session)
        existing = repo.get_price_snapshot(price.price_snapshot_id)
        if existing is not None:
            _same_or_error(existing, price, "price snapshot")
            return PriceRefreshResult(
                ticker=profile.ticker,
                session_date=session_date,
                status=RefreshStatus.ALREADY_EXISTS,
                price_snapshot_id=price.price_snapshot_id,
                observation_count=1,
            )
        repo.add_price_snapshot(price, instrument_id=profile.instrument_id)
        return PriceRefreshResult(
            ticker=profile.ticker,
            session_date=session_date,
            status=RefreshStatus.STORED,
            price_snapshot_id=price.price_snapshot_id,
            observation_count=1,
        )

    def refresh_eod(self, ticker: str, session_date: date) -> PriceRefreshResult:
        profile = self.profile(ticker)
        if not os.environ.get("TIINGO_API_TOKEN", "").strip():
            return PriceRefreshResult(
                ticker=profile.ticker,
                session_date=session_date,
                status=RefreshStatus.PENDING_CREDENTIAL,
                reason="TIINGO_API_TOKEN is not set",
            )
        client = TiingoClient.from_environment()
        source = TiingoHistoricalPriceSource(client)
        result = source.adjusted_prices(
            HistoricalSecurityCandidate(
                permanent_id=profile.instrument_id,
                company_id=profile.company_id,
                instrument_id=profile.instrument_id,
                ticker=profile.ticker,
                exchange=profile.exchange,
                anchor_date=session_date,
            ),
            start=session_date,
            end=session_date,
        )
        if result.value is None:
            reason = ",".join(item.detail for item in result.failures)
            return PriceRefreshResult(
                ticker=profile.ticker,
                session_date=session_date,
                status=RefreshStatus.UNAVAILABLE,
                reason=reason or "no exact-session price",
            )
        exact = tuple(
            item for item in result.value.observations if item.date == session_date
        )
        if len(exact) != 1:
            return PriceRefreshResult(
                ticker=profile.ticker,
                session_date=session_date,
                status=RefreshStatus.UNAVAILABLE,
                observation_count=len(result.value.observations),
                reason="requested session has no unique Tiingo observation",
            )
        snapshots = tiingo_to_price_snapshots(
            result.value.model_copy(update={"observations": exact}),
            basis=PriceBasis.RAW,
            evidence=TiingoAdjustmentEvidence(
                split_validation_passed=False,
                dividend_validation_passed=False,
                note="RAW valuation path; adjustment evidence is not required",
            ),
            currency=profile.currency,
        )
        snapshot = snapshots[0].model_copy(
            update={"company_id": profile.company_id}
        )
        return self.store_raw_close(profile.ticker, session_date, snapshot)

    def _unresolved_grade(
        self,
        *,
        profile: DemoProfile,
        price: PriceSnapshot,
        assessment_as_of: datetime,
        policy_version: InvestmentGradePolicyVersion,
        reason: str,
    ) -> InvestmentGradeSnapshot:
        return InvestmentGradeSnapshot(
            snapshot_id=(
                f"{_evaluation_id(profile.analysis.snapshot_id, price.price_snapshot_id, policy_version)}-ig"
            ),
            ticker=profile.ticker,
            model_version=(
                INVESTMENT_GRADE_V1_1_MODEL_VERSION
                if policy_version == InvestmentGradePolicyVersion.V1_1
                else "investment-grade-v1-frozen"
            ),
            initial_valuation_grade=InvestmentGrade.U,
            final_grade=InvestmentGrade.U,
            adjustments=(
                InvestmentGradeAdjustment(
                    sequence=1,
                    adjustment_type=AdjustmentType.GATE,
                    trigger=InvestmentGradeTrigger.VALUATION_CONFIDENCE,
                    active=True,
                    maximum_grade=InvestmentGrade.U,
                    reason=VALUATION_UNRESOLVED,
                ),
            ),
            rationale=reason,
            period_end=profile.analysis.period_end,
            available_at=price.timestamp,
            as_of=assessment_as_of,
        )

    def revalue(
        self,
        ticker: str,
        price_snapshot_id: str,
        *,
        policy_version: InvestmentGradePolicyVersion = InvestmentGradePolicyVersion.V1_1,
        assessment_as_of: datetime | None = None,
        created_at: datetime | None = None,
    ) -> tuple[OperatingEvaluation, WriteStatus]:
        profile = self.profile(ticker)
        analysis = AnalysisRepository(self.session).get_analysis_snapshot(
            profile.analysis.snapshot_id
        )
        if analysis is None:
            raise ValueError("reference analysis is not seeded")
        price = PriceRepository(self.session).get_price_snapshot(price_snapshot_id)
        if price is None:
            raise ValueError("price snapshot is not stored")
        if price.ticker != profile.ticker or price.currency != profile.currency:
            raise ValueError("price identity/currency mismatch")
        if price.price_basis != PriceBasis.RAW:
            raise ValueError("valuation requires RAW price basis")
        assessment = assessment_as_of or max(price.timestamp, analysis.as_of)
        if analysis.as_of > assessment or analysis.available_at > assessment:
            raise ValueError("reference analysis information is not available at assessment")
        if price.timestamp > assessment:
            raise ValueError("price is not available at assessment_as_of")
        created = created_at or datetime.now(timezone.utc)
        if created < assessment:
            raise ValueError("created_at cannot precede assessment_as_of")

        valuation: ValuationSnapshot | None = None
        estimated_market_cap: float | None = None
        reasons: tuple[str, ...] = ()
        assumption_set_id: str | None = None
        assumption_version: int | None = None

        if analysis.case == AnalysisCase.CASE_1_PROFITABLE_GROWTH:
            reasons = (VALUATION_UNRESOLVED, "VALUATION_ASSUMPTIONS_UNAVAILABLE")
            grade = self._unresolved_grade(
                profile=profile,
                price=price,
                assessment_as_of=assessment,
                policy_version=policy_version,
                reason="VALUATION_ASSUMPTIONS_UNAVAILABLE",
            )
        else:
            if analysis.valuation is None:
                raise ValueError("Case 2 reference analysis has no valuation")
            assumption_set_id = analysis.valuation.assumption_set.assumption_set_id
            assumption_version = analysis.valuation.assumption_set.version
            assumptions = ValuationRepository(self.session).get_valuation_assumption(
                assumption_set_id, assumption_version
            )
            if assumptions is None or assumptions != analysis.valuation.assumption_set:
                raise ValueError("stored valuation assumption does not match reference analysis")
            if not profile.share_basis_confirmed:
                reasons = (VALUATION_UNRESOLVED, "SHARE_SPLIT_BASIS_UNRESOLVED")
                grade = self._unresolved_grade(
                    profile=profile,
                    price=price,
                    assessment_as_of=assessment,
                    policy_version=policy_version,
                    reason="SHARE_SPLIT_BASIS_UNRESOLVED",
                )
            else:
                if (
                    profile.current_revenue is None
                    or profile.shares_for_market_cap is None
                    or profile.reported_shares_as_of is None
                    or profile.valuation_evidence is None
                    or profile.asymmetry_type is None
                    or profile.required_return is None
                ):
                    raise ValueError("Case 2 DEMO profile lacks required valuation context")
                if profile.reported_shares_as_of > assessment:
                    raise ValueError("reported shares are not available at assessment_as_of")
                if any(item.as_of > assessment for item in assumptions.exit_multiples):
                    raise ValueError("valuation evidence is not available at assessment_as_of")
                estimated_market_cap = price.price * profile.shares_for_market_cap / 1000
                valuation = build_case2_valuation(
                    identity=ValuationIdentity(
                        snapshot_id=(
                            f"{_evaluation_id(analysis.snapshot_id, price.price_snapshot_id, policy_version)}-valuation"
                        ),
                        ticker=profile.ticker,
                        period_end=analysis.period_end,
                        available_at=price.timestamp,
                        as_of=assessment,
                    ),
                    assumptions=assumptions,
                    current_market_cap=estimated_market_cap,
                    current_revenue=profile.current_revenue,
                    required_return=profile.required_return,
                    evidence=profile.valuation_evidence,
                    asymmetry_type=profile.asymmetry_type,
                ).model_copy(
                    update={
                        "fundamental_input_fingerprint": profile.fundamental_input_fingerprint
                    }
                )
                narrative_gate = analysis.narrative_gate
                if narrative_gate is None:
                    raise ValueError(
                        "reference analysis narrative gate is unresolved; "
                        "price-only revaluation cannot invent missing evidence"
                    )
                grade_builder = (
                    build_investment_grade_v1_1
                    if policy_version == InvestmentGradePolicyVersion.V1_1
                    else build_investment_grade
                )
                extra = (
                    {
                        "meaningful_optionality": profile.meaningful_optionality,
                        "highly_stage_sensitive": profile.highly_stage_sensitive,
                    }
                    if policy_version == InvestmentGradePolicyVersion.V1_1
                    else {}
                )
                grade = grade_builder(
                    snapshot_id=(
                        f"{_evaluation_id(analysis.snapshot_id, price.price_snapshot_id, policy_version)}-ig"
                    ),
                    ticker=profile.ticker,
                    period_end=analysis.period_end,
                    available_at=price.timestamp,
                    as_of=assessment,
                    case=analysis.case,
                    quant=analysis.quant,
                    current_trend=analysis.current_trend,
                    narrative_gate=narrative_gate,
                    valuation=valuation,
                    thesis_breaker_triggered=profile.thesis_breaker_triggered,
                    **extra,
                )
                if grade.final_grade == InvestmentGrade.U:
                    reasons = tuple(
                        item.reason for item in grade.adjustments if item.active
                    ) or (grade.rationale or "INVESTMENT_GRADE_UNRESOLVED",)

        evaluation = OperatingEvaluation(
            evaluation_id=_evaluation_id(
                analysis.snapshot_id, price.price_snapshot_id, policy_version
            ),
            reference_analysis_snapshot_id=analysis.snapshot_id,
            instrument_id=profile.instrument_id,
            ticker=profile.ticker,
            case=analysis.case,
            price_snapshot_id=price.price_snapshot_id,
            price_session_date=price.timestamp.astimezone(US_MARKET_TIMEZONE).date(),
            price_timestamp=price.timestamp,
            price_basis=price.price_basis,
            price=price.price,
            currency=price.currency,
            assumption_set_id=assumption_set_id,
            assumption_version=assumption_version,
            fundamental_input_reference=profile.fundamental_input_reference,
            fundamental_input_fingerprint=profile.fundamental_input_fingerprint,
            investment_grade_policy_version=policy_version,
            assessment_as_of=assessment,
            financial_period_label=profile.financial_period_label,
            financial_available_at=analysis.available_at,
            original_analysis_as_of=analysis.as_of,
            reported_shares_as_of=profile.reported_shares_as_of,
            shares_for_market_cap=profile.shares_for_market_cap,
            estimated_market_cap=estimated_market_cap,
            valuation_result=valuation,
            investment_grade_result=grade,
            unresolved_reasons=reasons,
            created_at=created,
        )
        status = self.artifacts.append(evaluation)
        return evaluation, status

    def compare_evaluations(
        self,
        previous_evaluation_id: str,
        current_evaluation_id: str,
    ) -> OperatingEvaluationDiff:
        previous = self.artifacts.get(previous_evaluation_id)
        current = self.artifacts.get(current_evaluation_id)
        if previous is None or current is None:
            raise ValueError("both evaluation IDs must exist")
        if previous.ticker != current.ticker or previous.instrument_id != current.instrument_id:
            raise ValueError("evaluations must reference the same instrument")
        if current.assessment_as_of <= previous.assessment_as_of:
            raise ValueError("current evaluation must be later than previous evaluation")
        previous_price = PriceRepository(self.session).get_price_snapshot(
            previous.price_snapshot_id
        )
        current_price = PriceRepository(self.session).get_price_snapshot(
            current.price_snapshot_id
        )
        if previous_price is None or current_price is None:
            raise ValueError("evaluation price snapshot is missing")
        price_change = compare_prices(previous_price, current_price)
        same_assumption = (
            previous.assumption_set_id == current.assumption_set_id
            and previous.assumption_version == current.assumption_version
        )
        same_policy = (
            previous.investment_grade_policy_version
            == current.investment_grade_policy_version
        )
        same_fundamental = (
            previous.reference_analysis_snapshot_id
            == current.reference_analysis_snapshot_id
            and previous.fundamental_input_fingerprint
            == current.fundamental_input_fingerprint
        )
        if not same_policy:
            change_type = EvaluationChangeType.POLICY_CHANGE
        elif not same_assumption or not same_fundamental:
            change_type = EvaluationChangeType.ASSUMPTION_OR_EVIDENCE_CHANGE
        elif previous.price_snapshot_id != current.price_snapshot_id:
            change_type = EvaluationChangeType.PRICE_ONLY
        else:
            change_type = EvaluationChangeType.NONE

        def gap(item: OperatingEvaluation) -> str:
            if item.valuation_result is None:
                return "unresolved"
            return item.valuation_result.output.expectation_gap.value

        return OperatingEvaluationDiff(
            ticker=current.ticker,
            previous_evaluation_id=previous.evaluation_id,
            current_evaluation_id=current.evaluation_id,
            change_type=change_type,
            previous_price=previous.price,
            current_price=current.price,
            price_return=price_change.return_ratio,
            previous_expectation_gap=gap(previous),
            current_expectation_gap=gap(current),
            previous_grade=previous.investment_grade_result.final_grade,
            current_grade=current.investment_grade_result.final_grade,
            assumption_identity_unchanged=same_assumption,
            policy_version_unchanged=same_policy,
            fundamental_input_unchanged=same_fundamental,
            unresolved_reasons=current.unresolved_reasons,
        )


def open_limited_operating_service(
    *,
    repo_root: str | Path,
    db_path: str | Path = DEFAULT_DB_PATH,
    artifact_path: str | Path = DEFAULT_ARTIFACT_PATH,
) -> tuple[Session, LimitedOperatingService]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_sqlite_engine(path)
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    return session, LimitedOperatingService(
        session, repo_root=repo_root, artifact_path=artifact_path
    )


def exact_us_close_snapshot(
    *,
    ticker: str,
    company_id: str,
    session_date: date,
    close: float,
    retrieved_at: datetime,
    source: str,
    provider_reference: str,
    snapshot_id: str | None = None,
) -> PriceSnapshot:
    """Create an explicit RAW close; primarily useful to offline adapters and tests."""
    timestamp = datetime.combine(session_date, time(16, 0), US_MARKET_TIMEZONE)
    return PriceSnapshot(
        price_snapshot_id=snapshot_id or f"{source.lower()}-{ticker}-raw-{session_date}",
        ticker=ticker,
        company_id=company_id,
        timestamp=timestamp,
        price=close,
        currency="USD",
        source=source,
        price_type=PriceType.CLOSE,
        price_basis=PriceBasis.RAW,
        provider_reference=provider_reference,
        created_at=max(retrieved_at, timestamp),
    )


def evaluation_summary(evaluation: OperatingEvaluation) -> str:
    valuation = evaluation.valuation_result
    quant_or_current_note = (
        "preserved from reference AnalysisSnapshot; no fundamental re-analysis"
    )
    gap = valuation.output.expectation_gap.value if valuation else "unresolved"
    assumption = (
        f"{evaluation.assumption_set_id} / v{evaluation.assumption_version}"
        if evaluation.assumption_set_id
        else "unresolved"
    )
    unresolved = ", ".join(evaluation.unresolved_reasons) or "none"
    return "\n".join(
        (
            f"{evaluation.ticker} - {evaluation.usage_mode.value}",
            f"reference analysis: {evaluation.reference_analysis_snapshot_id} / {evaluation.original_analysis_as_of.isoformat()}",
            f"financial basis: {evaluation.financial_period_label} / available {evaluation.financial_available_at.isoformat()}",
            f"price: {evaluation.price_session_date.isoformat()} / RAW close {evaluation.price:.4f} {evaluation.currency}",
            f"assumptions: {assumption}",
            f"IG policy: {evaluation.investment_grade_result.model_version}",
            f"Quant/Current/Narrative: {quant_or_current_note}",
            f"Expectation Gap: {gap}",
            f"Investment Grade: {evaluation.investment_grade_result.final_grade.value}",
            f"limitations/unresolved: {unresolved}",
        )
    )


def diff_summary(diff: OperatingEvaluationDiff) -> str:
    return "\n".join(
        (
            f"{diff.ticker} - evaluation change",
            f"price: {diff.previous_price:.4f} -> {diff.current_price:.4f} ({diff.price_return:.2%})",
            f"Expectation Gap: {diff.previous_expectation_gap} -> {diff.current_expectation_gap}",
            f"Investment Grade: {diff.previous_grade.value} -> {diff.current_grade.value}",
            f"change type: {diff.change_type.value}",
        )
    )
