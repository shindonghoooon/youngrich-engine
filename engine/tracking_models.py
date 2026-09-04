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


class ValuationChangeType(str, Enum):
    PRICE_ONLY = "price_only"
    ASSUMPTION_CHANGE = "assumption_change"
    MIXED = "mixed"
    NONE = "none"


class GradeChangeReason(str, Enum):
    PRICE = "price"
    QUANT = "quant"
    CURRENT_TREND = "current_trend"
    NARRATIVE = "narrative"
    FUNDING = "funding"
    VALUATION_ASSUMPTION = "valuation_assumption"
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


class CurrentTrendSnapshot(TemporalSnapshot):
    snapshot_id: str
    ticker: str
    case: AnalysisCase
    model_version: str
    signals: tuple[CurrentTrendSignal, ...]
    overall: DirectionState
    flags: frozenset[TrendFlag] = frozenset()
    growth_scope: GrowthScope | None = None
    annual_quant_grade_reference: Grade | None = None

    @model_validator(mode="after")
    def validate_signal_names(self) -> Self:
        names = [signal.name for signal in self.signals]
        if len(names) != len(set(names)):
            raise ValueError("current signal names must be unique")
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
    output: ValuationOutput

    @model_validator(mode="after")
    def validate_resolution(self) -> Self:
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
    previous: bool
    current: bool
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


class PerformanceSnapshot(TemporalSnapshot):
    snapshot_id: str
    ticker: str
    analysis_snapshot_id: str
    entry_price: ExecutablePriceSnapshot
    current_price: float = Field(gt=0)
    total_return: float | None = None
    return_1m: float | None = None
    return_3m: float | None = None
    return_6m: float | None = None
    return_1y: float | None = None
    max_drawdown: float | None = None


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
        if self.quant.case != self.case:
            raise ValueError("QuantSnapshot case must match AnalysisSnapshot case")
        return self
