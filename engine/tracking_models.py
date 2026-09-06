"""Versioned domain models for historical analysis and tracking snapshots.

These models define storage contracts only. They do not implement or change any
Case 1 or Case 2 scoring, valuation, or investment-grade decision rule.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from engine.models import CapitalModel, Grade, Trend


class FrozenDomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TemporalSnapshot(FrozenDomainModel):
    period_end: date
    available_at: datetime
    as_of: datetime

    @model_validator(mode="after")
    def validate_information_timing(self) -> Self:
        if self.period_end > self.available_at.date():
            raise ValueError("period_end cannot be later than available_at")
        if self.available_at > self.as_of:
            raise ValueError("available_at cannot be later than as_of")
        return self


class AnalysisCase(str, Enum):
    CASE_1_PROFITABLE_GROWTH = "case1_profitable_growth"
    CASE_2_EMERGING_ASYMMETRIC_GROWTH = (
        "case2_emerging_asymmetric_growth"
    )


class ResolutionState(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class ChangeState(str, Enum):
    IMPROVED = "improved"
    UNCHANGED = "unchanged"
    DETERIORATED = "deteriorated"
    RESOLVED = "resolved"
    BECAME_UNRESOLVED = "became_unresolved"
    NOT_COMPARABLE = "not_comparable"


class KPIDirection(str, Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    CUSTOM = "custom"
    UNRESOLVED = "unresolved"


class PriceType(str, Enum):
    CLOSE = "close"
    EOD = "eod"
    DELAYED = "delayed"
    REALTIME = "realtime"


class PriceBasis(str, Enum):
    RAW = "raw"
    SPLIT_ADJUSTED = "split_adjusted"
    TOTAL_RETURN_ADJUSTED = "total_return_adjusted"


class PerformanceReturnType(str, Enum):
    PRICE_RETURN = "price_return"
    TOTAL_RETURN = "total_return"


class PerformanceHorizon(str, Enum):
    ONE_MONTH = "1m"
    THREE_MONTHS = "3m"
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"


class PriceSeriesCoverageStatus(str, Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    UNRESOLVED = "unresolved"


class AlphaComparisonIssue(str, Enum):
    BENCHMARK_UNAVAILABLE = "benchmark_unavailable"
    RETURN_TYPE_MISMATCH = "return_type_mismatch"
    START_DATE_MISMATCH = "start_date_mismatch"
    END_DATE_MISMATCH = "end_date_mismatch"


class ValuationChangeType(str, Enum):
    PRICE_ONLY = "price_only"
    ASSUMPTION_CHANGE = "assumption_change"
    FUNDAMENTAL_CHANGE = "fundamental_change"
    POLICY_CHANGE = "policy_change"
    MIXED = "mixed"
    UNRESOLVED = "unresolved"
    NONE = "none"


class GradeChangeReason(str, Enum):
    PRICE = "price"
    QUANT = "quant"
    CURRENT_TREND = "current_trend"
    NARRATIVE = "narrative"
    FUNDING = "funding"
    VALUATION_ASSUMPTION = "valuation_assumption"
    VALUATION_INPUT = "valuation_input"
    POLICY = "policy"
    THESIS_BREAKER = "thesis_breaker"
    CASE_MIGRATION = "case_migration"
    DATA_RESOLUTION = "data_resolution"
    MULTIPLE = "multiple"


class NarrativeState(str, Enum):
    PROVEN = "proven"
    STRONG = "strong"
    EMERGING = "emerging"
    WEAK = "weak"
    UNRESOLVED = "unresolved"


class NarrativeGate(str, Enum):
    CONFIRMED = "confirmed"
    QUALIFIED = "qualified"
    DEVELOPING = "developing"
    WEAK = "weak"
    BROKEN = "broken"
    UNRESOLVED = "unresolved"


class DirectionState(str, Enum):
    STRONG_POSITIVE = "strong_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"
    UNRESOLVED = "unresolved"


class TrendFlag(str, Enum):
    COMMERCIAL_INFLECTION = "commercial_inflection"
    FUNDING_STRESS = "funding_stress"
    COMMERCIAL_DETERIORATION = "commercial_deterioration"


class BinaryEvidenceState(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class GrowthScope(str, Enum):
    SAME_SCOPE = "same_scope"
    PRO_FORMA_COMPARABLE = "pro_forma_comparable"
    ACQUISITION_INFLUENCED = "acquisition_influenced"
    UNRESOLVED = "unresolved"


class InvestmentGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    X = "X"
    U = "U"


class InvestmentGradePolicyVersion(str, Enum):
    V1 = "v1"
    V1_1 = "v1.1"


class TerminalStage(str, Enum):
    GROWTH = "growth"
    TRANSITION = "transition"
    MATURE = "mature"


class ValuationConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNRESOLVED = "unresolved"


class ExpectationGap(str, Enum):
    POSITIVE = "positive"
    OVERLAP = "overlap"
    NEGATIVE = "negative"
    UNRESOLVED = "unresolved"


class AsymmetryType(str, Enum):
    FAVORABLE = "favorable"
    BALANCED = "balanced"
    UNFAVORABLE = "unfavorable"
    BINARY = "binary"
    UNRESOLVED = "unresolved"


class ThesisStatus(str, Enum):
    CONFIRMING = "confirming"
    NEUTRAL = "neutral"
    WEAKENING = "weakening"
    BROKEN = "broken"
    UNRESOLVED = "unresolved"

    @classmethod
    def _missing_(cls, value: object) -> "ThesisStatus | None":
        if isinstance(value, str) and value.lower() == "stable":
            return cls.NEUTRAL
        return None


class AdjustmentType(str, Enum):
    GATE = "gate"
    CAP = "cap"


class InvestmentGradeTrigger(str, Enum):
    QUANT = "quant"
    CURRENT_TREND = "current_trend"
    NARRATIVE = "narrative"
    FUNDING_STRESS = "funding_stress"
    COMMERCIAL_INFLECTION = "commercial_inflection"
    COMMERCIAL_DETERIORATION = "commercial_deterioration"
    VALUATION_CONFIDENCE = "valuation_confidence"
    THESIS_BREAKER = "thesis_breaker"


class ExitMultipleEvidenceSource(str, Enum):
    COMPANY_HISTORY = "company_history"
    COMPARABLE_COMPANIES = "comparable_companies"
    BUSINESS_CAPITAL_MODEL = "business_capital_model"


class ExitMultipleBand(str, Enum):
    CONSERVATIVE = "conservative"
    BASE = "base"
    PREMIUM = "premium"


class ValuationMetric(str, Enum):
    PE = "pe"
    EV_REVENUE = "ev_revenue"
    EV_GROSS_PROFIT = "ev_gross_profit"
    EV_EBIT = "ev_ebit"
    FCF = "fcf"


class MetricResult(FrozenDomainModel):
    name: str
    state: ResolutionState
    value: float | str | bool | None = None
    unit: str | None = None
    grade: Grade | None = None
    trend: Trend = Trend.NA
    weight: float = Field(default=0.0, ge=0, le=1)
    is_core: bool = True
    supporting_tags: tuple[str, ...] = ()
    note: str | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> Self:
        if not self.is_core and self.weight != 0:
            raise ValueError("supporting metric weight must be zero")
        if self.state == ResolutionState.UNRESOLVED:
            if self.value is not None or self.grade is not None:
                raise ValueError("unresolved metric cannot have a value or grade")
        elif self.value is None:
            raise ValueError("resolved metric requires a value")
        return self


class GradeCap(FrozenDomainModel):
    trigger: str
    maximum_grade: Grade
    active: bool
    reason: str


class QuantSnapshot(TemporalSnapshot):
    snapshot_id: str
    ticker: str
    case: AnalysisCase
    model_version: str
    metrics: tuple[MetricResult, ...]
    state: ResolutionState
    score: float | None = None
    uncapped_grade: Grade | None = None
    grade: Grade | None = None
    grade_caps: tuple[GradeCap, ...] = ()
    growth_scope: GrowthScope | None = None
    coverage: float = Field(default=1.0, ge=0, le=1)
    provisional: bool = False

    @model_validator(mode="after")
    def validate_quant_contract(self) -> Self:
        names = [metric.name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError("metric names must be unique within a QuantSnapshot")
        core_weight = sum(metric.weight for metric in self.metrics if metric.is_core)
        if abs(core_weight - 1.0) > 1e-9:
            raise ValueError("core metric weights must sum to 1.0")
        if self.state == ResolutionState.UNRESOLVED:
            if (
                self.score is not None
                or self.uncapped_grade is not None
                or self.grade is not None
            ):
                raise ValueError("unresolved QuantSnapshot cannot have score or grade")
        elif self.score is None or self.grade is None:
            raise ValueError("resolved QuantSnapshot requires score and grade")
        if (
            self.state == ResolutionState.RESOLVED
            and self.coverage < 1.0
            and not self.provisional
        ):
            raise ValueError("partial metric coverage must be marked provisional")
        return self


class CurrentTrendSignal(FrozenDomainModel):
    name: str
    state: DirectionState
    observation: str | None = None


class TrendFlagResult(FrozenDomainModel):
    flag: TrendFlag
    state: BinaryEvidenceState


class CurrentTrendSnapshot(TemporalSnapshot):
    snapshot_id: str
    ticker: str
    case: AnalysisCase
    model_version: str
    signals: tuple[CurrentTrendSignal, ...]
    overall: DirectionState
    flags: frozenset[TrendFlag] = frozenset()
    flag_results: tuple[TrendFlagResult, ...] = ()
    growth_scope: GrowthScope | None = None
    annual_quant_grade_reference: Grade | None = None

    @model_validator(mode="after")
    def validate_signal_names(self) -> Self:
        names = [signal.name for signal in self.signals]
        if len(names) != len(set(names)):
            raise ValueError("current signal names must be unique")
        flag_names = [item.flag for item in self.flag_results]
        if len(flag_names) != len(set(flag_names)):
            raise ValueError("current flag results must be unique")
        if self.flag_results:
            active = frozenset(
                item.flag
                for item in self.flag_results
                if item.state == BinaryEvidenceState.YES
            )
            if active != self.flags:
                raise ValueError("flags must contain exactly the YES flag results")
        return self


class NarrativeAssessment(FrozenDomainModel):
    dimension: str
    state: NarrativeState
    evidence: tuple[str, ...] = ()
    note: str | None = None


class NarrativeSnapshot(TemporalSnapshot):
    snapshot_id: str
    ticker: str
    case: AnalysisCase
    model_version: str
    thesis_id: str
    thesis_version: int = Field(ge=1)
    kpi_set_version: int = Field(ge=1)
    kpi_definition_ids: tuple[str, ...]
    assessments: tuple[NarrativeAssessment, ...]
    overall: NarrativeState

    @model_validator(mode="after")
    def validate_narrative_contract(self) -> Self:
        if len(self.kpi_definition_ids) != len(set(self.kpi_definition_ids)):
            raise ValueError("narrative KPI definition ids must be unique")
        dimensions = [assessment.dimension for assessment in self.assessments]
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("narrative dimensions must be unique")
        return self


class ThesisDefinition(FrozenDomainModel):
    thesis_id: str
    ticker: str
    version: int = Field(ge=1)
    case: AnalysisCase
    title: str
    thesis: str
    failure_mode: str
    kpi_set_version: int = Field(ge=1)
    kpi_definition_ids: tuple[str, ...]
    effective_from: datetime

    @model_validator(mode="after")
    def validate_kpi_definition_ids(self) -> Self:
        if len(self.kpi_definition_ids) != len(set(self.kpi_definition_ids)):
            raise ValueError("thesis KPI definition ids must be unique")
        return self


class TrackingKPIDefinition(FrozenDomainModel):
    kpi_definition_id: str
    ticker: str
    kpi_key: str
    thesis_id: str
    thesis_version: int = Field(ge=1)
    kpi_set_version: int = Field(ge=1)
    name: str
    unit: str
    direction: KPIDirection
    is_primary: bool = True
    source_requirement: str
    confirming_condition: str
    weakening_condition: str
    breaker_condition: str | None = None


class TrackingKPIObservation(TemporalSnapshot):
    observation_id: str
    ticker: str
    kpi_definition_id: str
    kpi_key: str
    thesis_version: int = Field(ge=1)
    kpi_set_version: int = Field(ge=1)
    state: ResolutionState
    value: float | str | bool | None = None
    interpreted_direction: DirectionState | None = None
    source_reference: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_observation_resolution(self) -> Self:
        if self.state == ResolutionState.UNRESOLVED and self.value is not None:
            raise ValueError("unresolved KPI observation cannot have a value")
        if self.state == ResolutionState.RESOLVED and self.value is None:
            raise ValueError("resolved KPI observation requires a value")
        return self


class ThesisStatusSnapshot(TemporalSnapshot):
    snapshot_id: str
    ticker: str
    thesis_id: str
    thesis_version: int = Field(ge=1)
    kpi_set_version: int = Field(ge=1)
    observation_ids: tuple[str, ...]
    status: ThesisStatus
    breaker_triggered: bool = False
    material_narrative_deterioration: bool = False
    note: str | None = None


class PriceSnapshot(FrozenDomainModel):
    price_snapshot_id: str
    ticker: str
    company_id: str | None = None
    timestamp: datetime
    price: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    market_cap: float | None = Field(default=None, gt=0)
    enterprise_value: float | None = None
    source: str
    price_type: PriceType
    price_basis: PriceBasis = PriceBasis.RAW
    adjustment_version: str | None = None
    provider_reference: str | None = None
    analysis_snapshot_id: str | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_price_timing(self) -> Self:
        for field_name, value in (
            ("timestamp", self.timestamp),
            ("created_at", self.created_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        if self.created_at < self.timestamp:
            raise ValueError("created_at cannot precede price timestamp")
        return self


class AssumptionRange(FrozenDomainModel):
    low: float
    high: float

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.low > self.high:
            raise ValueError("assumption range must be low <= high")
        return self


class ExitMultipleAssumption(FrozenDomainModel):
    band: ExitMultipleBand
    metric_type: ValuationMetric
    value: float = Field(gt=0)
    evidence_type: ExitMultipleEvidenceSource
    source_reference: str
    as_of: datetime
    rationale: str

    @model_validator(mode="after")
    def validate_evidence_timing(self) -> Self:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("exit-multiple evidence as_of must be timezone-aware")
        return self


class ValuationAssumptionSet(FrozenDomainModel):
    assumption_set_id: str
    version: int = Field(ge=1)
    case: AnalysisCase
    required_return_sensitivities: tuple[float, ...] = (0.10, 0.15, 0.20)
    default_required_return: float = 0.15
    horizon_years: int = Field(gt=0)
    terminal_stage: TerminalStage
    terminal_stage_rationale: str
    terminal_stage_confidence: ValuationConfidence
    primary_metric: ValuationMetric
    exit_multiples: tuple[ExitMultipleAssumption, ...]
    plausible_growth_range: AssumptionRange | None = None
    expected_annual_dilution: float | None = None
    target_gross_margin: float | None = None
    target_operating_margin: float | None = None
    terminal_net_debt: float | None = None
    notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_required_return(self) -> Self:
        if set(self.required_return_sensitivities) != {0.10, 0.15, 0.20}:
            raise ValueError("required return sensitivities must be 10%, 15%, and 20%")
        if self.default_required_return not in self.required_return_sensitivities:
            raise ValueError("default required return must be in sensitivity set")
        bands = [multiple.band for multiple in self.exit_multiples]
        if len(bands) != len(set(bands)):
            raise ValueError("exit multiple bands must be unique")
        if set(bands) != set(ExitMultipleBand):
            raise ValueError("conservative, base, and premium multiples are required")
        if any(
            multiple.metric_type != self.primary_metric
            for multiple in self.exit_multiples
        ):
            raise ValueError("exit multiple metric must match configured primary metric")
        if self.plausible_growth_range is None:
            raise ValueError("a versioned plausible growth range is required")
        if self.case == AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH:
            if self.expected_annual_dilution is None or self.terminal_net_debt is None:
                raise ValueError("Case 2 requires dilution and terminal net debt assumptions")
            if (
                self.primary_metric == ValuationMetric.EV_GROSS_PROFIT
                and self.target_gross_margin is None
            ):
                raise ValueError("EV/GP requires a target gross margin assumption")
            if (
                self.primary_metric == ValuationMetric.EV_EBIT
                and self.target_operating_margin is None
            ):
                raise ValueError("EV/EBIT requires a target operating margin assumption")
        return self


def validate_valuation_evidence_timing(
    *,
    evaluation_as_of: datetime,
    assumption_set: ValuationAssumptionSet,
    evidence_available_at: datetime | None,
    evidence_retrieved_at: datetime | None = None,
    require_evidence_available_at: bool = False,
) -> None:
    """Validate public-information timing without treating retrieval as publication.

    ``evidence_retrieved_at`` is retained for provenance and only needs to be a valid
    aware timestamp. A source may be retrieved after an historical analysis cutoff when
    its independently recorded publication/availability time was already public.
    """
    if evaluation_as_of.tzinfo is None or evaluation_as_of.utcoffset() is None:
        raise ValueError("valuation evaluation_as_of must be timezone-aware")
    if evidence_available_at is None:
        if require_evidence_available_at:
            raise ValueError("valuation evidence available_at is required")
    else:
        if (
            evidence_available_at.tzinfo is None
            or evidence_available_at.utcoffset() is None
        ):
            raise ValueError("valuation evidence available_at must be timezone-aware")
        if evidence_available_at > evaluation_as_of:
            raise ValueError("valuation evidence is not available at valuation as_of")
    if evidence_retrieved_at is not None and (
        evidence_retrieved_at.tzinfo is None
        or evidence_retrieved_at.utcoffset() is None
    ):
        raise ValueError("valuation evidence retrieved_at must be timezone-aware")
    if any(item.as_of > evaluation_as_of for item in assumption_set.exit_multiples):
        raise ValueError("exit-multiple evidence is not available at valuation as_of")


class ValuationOutput(FrozenDomainModel):
    required_growth: float | None = None
    required_growth_range: AssumptionRange | None = None
    required_growth_cases: tuple["RequiredGrowthCase", ...] = ()
    expectation_gap: ExpectationGap = ExpectationGap.UNRESOLVED
    bear_value: float | None = None
    base_value: float | None = None
    bull_value: float | None = None
    downside_severity: str | None = None
    upside_optionality: str | None = None
    asymmetry_type: AsymmetryType = AsymmetryType.UNRESOLVED
    confidence: ValuationConfidence = ValuationConfidence.UNRESOLVED


class RequiredGrowthCase(FrozenDomainModel):
    band: ExitMultipleBand
    exit_multiple: float = Field(gt=0)
    required_growth: float
    required_future_equity_value: float | None = None
    required_future_enterprise_value: float | None = None
    required_future_revenue: float | None = None


class ValuationSnapshot(TemporalSnapshot):
    snapshot_id: str
    ticker: str
    assumption_set: ValuationAssumptionSet
    state: ResolutionState
    market_price: float | None = Field(default=None, gt=0)
    market_cap: float | None = Field(default=None, gt=0)
    fundamental_input_fingerprint: str | None = None
    evidence_available_at: datetime | None = None
    evidence_retrieved_at: datetime | None = None
    output: ValuationOutput

    @model_validator(mode="after")
    def validate_resolution(self) -> Self:
        validate_valuation_evidence_timing(
            evaluation_as_of=self.as_of,
            assumption_set=self.assumption_set,
            evidence_available_at=self.evidence_available_at,
            evidence_retrieved_at=self.evidence_retrieved_at,
        )
        if self.assumption_set.case == AnalysisCase.CASE_1_PROFITABLE_GROWTH:
            if self.market_price is None:
                raise ValueError("Case 1 valuation requires market_price")
        elif self.market_cap is None:
            raise ValueError("Case 2 valuation requires market_cap")
        if self.state == ResolutionState.UNRESOLVED:
            values = (
                self.output.required_growth,
                self.output.bear_value,
                self.output.base_value,
                self.output.bull_value,
            )
            if any(value is not None for value in values):
                raise ValueError("unresolved valuation cannot contain numeric outputs")
        return self

    def reprice(
        self,
        *,
        snapshot_id: str,
        period_end: date,
        available_at: datetime,
        as_of: datetime,
        market_price: float,
        output: ValuationOutput,
    ) -> "ValuationSnapshot":
        """Create a price-only snapshot while preserving assumption identity/version."""
        return ValuationSnapshot(
            snapshot_id=snapshot_id,
            ticker=self.ticker,
            period_end=period_end,
            available_at=available_at,
            as_of=as_of,
            assumption_set=self.assumption_set,
            state=self.state,
            market_price=market_price,
            market_cap=self.market_cap,
            fundamental_input_fingerprint=self.fundamental_input_fingerprint,
            evidence_available_at=self.evidence_available_at,
            evidence_retrieved_at=self.evidence_retrieved_at,
            output=output,
        )


class InvestmentGradeAdjustment(FrozenDomainModel):
    sequence: int = Field(ge=1)
    adjustment_type: AdjustmentType
    trigger: InvestmentGradeTrigger
    active: bool
    maximum_grade: InvestmentGrade | None = None
    reason: str

    @model_validator(mode="after")
    def validate_cap(self) -> Self:
        if self.adjustment_type == AdjustmentType.CAP and self.maximum_grade is None:
            raise ValueError("cap adjustment requires maximum_grade")
        return self


class InvestmentGradeSnapshot(TemporalSnapshot):
    snapshot_id: str
    ticker: str
    model_version: str
    initial_valuation_grade: InvestmentGrade
    final_grade: InvestmentGrade
    adjustments: tuple[InvestmentGradeAdjustment, ...] = ()
    thesis_breaker_active: bool = False
    rationale: str | None = None

    @model_validator(mode="after")
    def validate_adjustment_order(self) -> Self:
        sequences = [adjustment.sequence for adjustment in self.adjustments]
        if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
            raise ValueError("Investment Grade adjustments must have unique sequence order")
        return self


class SnapshotChange(FrozenDomainModel):
    field: str
    previous: str | int | float | bool | None = None
    current: str | int | float | bool | None = None


class MetricDiff(FrozenDomainModel):
    metric_key: str
    previous_state: ResolutionState | None = None
    current_state: ResolutionState | None = None
    previous_value: float | str | bool | None = None
    current_value: float | str | bool | None = None
    previous_grade: Grade | None = None
    current_grade: Grade | None = None
    change: ChangeState


class SignalDiff(FrozenDomainModel):
    signal_key: str
    previous: DirectionState | None = None
    current: DirectionState | None = None
    change: ChangeState


class NarrativeDiff(FrozenDomainModel):
    dimension: str
    previous: NarrativeState | None = None
    current: NarrativeState | None = None
    change: ChangeState


class FlagDiff(FrozenDomainModel):
    flag: TrendFlag
    previous: bool | None
    current: bool | None
    change: ChangeState
    material: bool


class GradeChangeAttribution(FrozenDomainModel):
    previous_grade: InvestmentGrade | None = None
    current_grade: InvestmentGrade | None = None
    reasons: frozenset[GradeChangeReason] = frozenset()


class PriceChange(FrozenDomainModel):
    ticker: str
    previous_timestamp: datetime
    current_timestamp: datetime
    previous_price: float
    current_price: float
    absolute_change: float
    return_ratio: float
    market_cap_change: float | None = None
    enterprise_value_change: float | None = None


class EntryZoneBand(FrozenDomainModel):
    band: ExitMultipleBand
    exit_multiple: float = Field(gt=0)
    maximum_market_cap: float | None = Field(default=None, gt=0)
    entry_price: float | None = Field(default=None, gt=0)


class EntryZoneResult(FrozenDomainModel):
    ticker: str
    valuation_assumption_set_id: str
    valuation_assumption_version: int = Field(ge=1)
    target_state: ExpectationGap
    bands: tuple[EntryZoneBand, ...]
    currency: str = Field(min_length=3, max_length=3)
    required_return: float
    horizon_years: int = Field(gt=0)
    plausible_growth_used: float
    rationale: str


class SnapshotDiff(FrozenDomainModel):
    previous_snapshot_id: str
    current_snapshot_id: str
    previous_kpi_set_version: int = Field(ge=1)
    current_kpi_set_version: int = Field(ge=1)
    previous_kpi_definition_ids: tuple[str, ...]
    current_kpi_definition_ids: tuple[str, ...]
    narrative_kpi_set_changed: bool
    changes: tuple[SnapshotChange, ...] = ()
    ticker: str | None = None
    previous_as_of: datetime | None = None
    current_as_of: datetime | None = None
    metric_changes: tuple[MetricDiff, ...] = ()
    signal_changes: tuple[SignalDiff, ...] = ()
    narrative_changes: tuple[NarrativeDiff, ...] = ()
    flag_changes: tuple[FlagDiff, ...] = ()
    valuation_change_type: ValuationChangeType = ValuationChangeType.NONE
    grade_attribution: GradeChangeAttribution | None = None
    material_changes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def prevent_silent_narrative_kpi_change(self) -> Self:
        ids_changed = (
            self.previous_kpi_definition_ids
            != self.current_kpi_definition_ids
        )
        version_changed = (
            self.previous_kpi_set_version != self.current_kpi_set_version
        )
        if ids_changed and not version_changed:
            raise ValueError("narrative KPI ids changed without a kpi_set_version change")
        if ids_changed != self.narrative_kpi_set_changed:
            raise ValueError("narrative_kpi_set_changed must match the KPI id change")
        return self


class ExecutablePriceSnapshot(FrozenDomainModel):
    information_available_at: datetime
    executable_at: datetime
    price: float = Field(gt=0)
    source_reference: str

    @model_validator(mode="after")
    def validate_execution_timing(self) -> Self:
        if self.executable_at < self.information_available_at:
            raise ValueError(
                "executable price cannot precede required information availability"
            )
        return self


class PriceSeriesCoverage(FrozenDomainModel):
    status: PriceSeriesCoverageStatus
    observation_count: int = Field(ge=0)
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    maximum_observed_gap_days: int | None = Field(default=None, ge=0)
    reason: str | None = None

    @model_validator(mode="after")
    def validate_coverage(self) -> Self:
        if self.observation_count == 0:
            if any(value is not None for value in (self.first_timestamp, self.last_timestamp, self.maximum_observed_gap_days)):
                raise ValueError("empty coverage cannot contain observed timestamps or gaps")
        else:
            if self.first_timestamp is None or self.last_timestamp is None:
                raise ValueError("observed coverage requires first and last timestamps")
            for field_name, value in (("first_timestamp", self.first_timestamp), ("last_timestamp", self.last_timestamp)):
                if value.tzinfo is None or value.utcoffset() is None:
                    raise ValueError(f"{field_name} must be timezone-aware")
            if self.last_timestamp < self.first_timestamp:
                raise ValueError("coverage last_timestamp cannot precede first_timestamp")
        if self.observation_count >= 2 and self.maximum_observed_gap_days is None:
            raise ValueError("two or more observations require maximum gap")
        if self.status == PriceSeriesCoverageStatus.SUFFICIENT and self.observation_count < 2:
            raise ValueError("sufficient MDD coverage requires at least two observations")
        if self.status != PriceSeriesCoverageStatus.SUFFICIENT and not self.reason:
            raise ValueError("non-sufficient coverage requires a reason")
        return self


class HorizonPerformance(FrozenDomainModel):
    horizon: PerformanceHorizon
    state: ResolutionState
    target_date: date
    end_price_snapshot_id: str | None = None
    end_price: float | None = Field(default=None, gt=0)
    stock_return: float | None = None
    stock_start_effective_date: date | None = None
    stock_end_effective_date: date | None = None
    benchmark_end_price_snapshot_id: str | None = None
    benchmark_end_price: float | None = Field(default=None, gt=0)
    benchmark_return: float | None = None
    benchmark_return_type: PerformanceReturnType | None = None
    benchmark_start_effective_date: date | None = None
    benchmark_end_effective_date: date | None = None
    alpha_state: ResolutionState = ResolutionState.UNRESOLVED
    alpha: float | None = None
    alpha_unresolved_reason: AlphaComparisonIssue | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> Self:
        stock_fields = (self.end_price_snapshot_id, self.end_price, self.stock_return)
        if self.state == ResolutionState.UNRESOLVED and any(
            value is not None for value in stock_fields
        ):
            raise ValueError("unresolved horizon cannot contain stock return data")
        if self.state == ResolutionState.RESOLVED and any(
            value is None for value in stock_fields
        ):
            raise ValueError("resolved horizon requires end price and stock return")
        if self.state == ResolutionState.RESOLVED and (
            self.stock_start_effective_date is None or self.stock_end_effective_date is None
        ):
            raise ValueError("resolved horizon requires stock effective dates")
        benchmark_fields = (
            self.benchmark_end_price_snapshot_id,
            self.benchmark_end_price,
            self.benchmark_return,
            self.benchmark_return_type,
            self.benchmark_start_effective_date,
            self.benchmark_end_effective_date,
        )
        present = [value is not None for value in benchmark_fields]
        if self.state == ResolutionState.UNRESOLVED and any(present):
            raise ValueError("unresolved horizon cannot contain benchmark data")
        if any(present) and not all(present):
            raise ValueError("benchmark horizon data must be complete when present")
        if self.alpha_state == ResolutionState.RESOLVED:
            if self.alpha is None or not all(present):
                raise ValueError("resolved alpha requires complete comparable benchmark data")
            if self.alpha_unresolved_reason is not None:
                raise ValueError("resolved alpha cannot have an unresolved reason")
            if self.benchmark_return_type is None:
                raise ValueError("resolved alpha requires benchmark return type")
            if self.stock_start_effective_date != self.benchmark_start_effective_date:
                raise ValueError("resolved alpha requires matching effective start dates")
            if self.stock_end_effective_date != self.benchmark_end_effective_date:
                raise ValueError("resolved alpha requires matching effective end dates")
        elif self.alpha is not None:
            raise ValueError("unresolved alpha cannot contain a value")
        if self.alpha_state == ResolutionState.UNRESOLVED and any(present) and self.alpha_unresolved_reason is None:
            raise ValueError("unresolved alpha with benchmark data requires a structured reason")
        return self


class BenchmarkAssignment(FrozenDomainModel):
    assignment_id: str
    instrument_id: str
    benchmark_instrument_id: str
    version: int = Field(ge=1)
    valid_from: datetime
    rationale: str
    created_at: datetime

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        for field_name, value in (
            ("valid_from", self.valid_from),
            ("created_at", self.created_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        return self


class PerformanceSnapshot(FrozenDomainModel):
    performance_snapshot_id: str
    ticker: str
    analysis_snapshot_id: str
    instrument_id: str
    evaluation_as_of: datetime
    return_type: PerformanceReturnType
    price_basis: PriceBasis
    start_price_snapshot_id: str | None = None
    start_price: float | None = Field(default=None, gt=0)
    benchmark_assignment_id: str | None = None
    benchmark_assignment_version: int | None = Field(default=None, ge=1)
    benchmark_instrument_id: str | None = None
    benchmark_return_type: PerformanceReturnType | None = None
    benchmark_price_basis: PriceBasis | None = None
    benchmark_start_price_snapshot_id: str | None = None
    benchmark_start_price: float | None = Field(default=None, gt=0)
    horizons: tuple[HorizonPerformance, ...]
    return_since_analysis: float | None = None
    max_drawdown: float | None = None
    mdd_coverage: PriceSeriesCoverage
    state: ResolutionState
    coverage: float = Field(ge=0, le=1)
    calculation_version: str
    created_at: datetime
    note: str | None = None

    @model_validator(mode="after")
    def validate_performance_contract(self) -> Self:
        for field_name, value in (
            ("evaluation_as_of", self.evaluation_as_of),
            ("created_at", self.created_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        horizon_names = [item.horizon for item in self.horizons]
        if len(horizon_names) != len(set(horizon_names)):
            raise ValueError("performance horizons must be unique")
        if set(horizon_names) != set(PerformanceHorizon):
            raise ValueError("1M, 3M, 6M, and 1Y horizons are required")
        resolved = sum(item.state == ResolutionState.RESOLVED for item in self.horizons)
        if abs(self.coverage - resolved / len(PerformanceHorizon)) > 1e-9:
            raise ValueError("coverage must equal resolved horizons / expected horizons")
        start_fields = (self.start_price_snapshot_id, self.start_price)
        if self.state == ResolutionState.UNRESOLVED and any(
            value is not None for value in start_fields
        ):
            raise ValueError("unresolved performance cannot contain a start price")
        if self.state == ResolutionState.UNRESOLVED and (
            resolved or self.return_since_analysis is not None or self.max_drawdown is not None
        ):
            raise ValueError("unresolved performance cannot contain calculated results")
        if self.state == ResolutionState.RESOLVED and any(
            value is None for value in start_fields
        ):
            raise ValueError("resolved performance requires the analysis start price")
        benchmark_identity = (
            self.benchmark_assignment_id,
            self.benchmark_assignment_version,
            self.benchmark_instrument_id,
            self.benchmark_return_type,
            self.benchmark_price_basis,
        )
        identity_present = [value is not None for value in benchmark_identity]
        if any(identity_present) and not all(identity_present):
            raise ValueError("benchmark assignment identity must be complete")
        benchmark_start = (
            self.benchmark_start_price_snapshot_id,
            self.benchmark_start_price,
        )
        start_present = [value is not None for value in benchmark_start]
        if any(start_present) and not all(start_present):
            raise ValueError("benchmark start price must be complete")
        if any(start_present) and not all(identity_present):
            raise ValueError("benchmark start price requires an assignment")
        if self.price_basis == PriceBasis.RAW and self.state == ResolutionState.RESOLVED:
            raise ValueError("raw prices are not corporate-action-safe for performance")
        expected_type = {
            PriceBasis.SPLIT_ADJUSTED: PerformanceReturnType.PRICE_RETURN,
            PriceBasis.TOTAL_RETURN_ADJUSTED: PerformanceReturnType.TOTAL_RETURN,
        }.get(self.price_basis)
        if self.state == ResolutionState.RESOLVED and self.return_type != expected_type:
            raise ValueError("return type is incompatible with adjusted price basis")
        benchmark_expected_type = {
            PriceBasis.SPLIT_ADJUSTED: PerformanceReturnType.PRICE_RETURN,
            PriceBasis.TOTAL_RETURN_ADJUSTED: PerformanceReturnType.TOTAL_RETURN,
        }.get(self.benchmark_price_basis)
        if self.benchmark_return_type is not None and self.benchmark_return_type != benchmark_expected_type:
            raise ValueError("benchmark return type is incompatible with its price basis")
        if self.max_drawdown is not None and self.max_drawdown > 0:
            raise ValueError("max drawdown must be zero or negative")
        if self.mdd_coverage.status == PriceSeriesCoverageStatus.SUFFICIENT:
            if self.max_drawdown is None:
                raise ValueError("sufficient MDD coverage requires max_drawdown")
        elif self.max_drawdown is not None:
            raise ValueError("non-sufficient MDD coverage cannot contain max_drawdown")
        if self.created_at < self.evaluation_as_of:
            raise ValueError("created_at cannot precede evaluation_as_of")
        return self


class AnalysisSnapshot(TemporalSnapshot):
    snapshot_id: str
    ticker: str
    company_name: str
    case: AnalysisCase
    case_definition_version: str
    capital_model: CapitalModel | None = None
    quant: QuantSnapshot
    current_trend: CurrentTrendSnapshot | None = None
    narrative: NarrativeSnapshot | None = None
    thesis_status: ThesisStatusSnapshot | None = None
    valuation: ValuationSnapshot | None = None
    investment_grade: InvestmentGradeSnapshot | None = None
    narrative_gate: NarrativeGate | None = None
    reference_price_snapshot_id: str | None = None

    @model_validator(mode="after")
    def validate_component_identity_and_timing(self) -> Self:
        components = (
            self.quant,
            self.current_trend,
            self.narrative,
            self.thesis_status,
            self.valuation,
            self.investment_grade,
        )
        for component in components:
            if component is None:
                continue
            if component.ticker != self.ticker:
                raise ValueError("component ticker must match AnalysisSnapshot ticker")
            if component.available_at > self.as_of:
                raise ValueError("component available_at cannot be later than analysis as_of")
        if self.valuation is not None:
            validate_valuation_evidence_timing(
                evaluation_as_of=self.as_of,
                assumption_set=self.valuation.assumption_set,
                evidence_available_at=self.valuation.evidence_available_at,
                evidence_retrieved_at=self.valuation.evidence_retrieved_at,
            )
        if self.quant.case != self.case:
            raise ValueError("QuantSnapshot case must match AnalysisSnapshot case")
        return self
