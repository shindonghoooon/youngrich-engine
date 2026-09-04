"""Case-agnostic research contracts for historical calibration.

These immutable models link canonical analysis and performance snapshots. They do not
store duplicate investment calculations and cannot mutate frozen investment policy.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Self

from pydantic import Field, model_validator

from engine.tracking_models import (
    DirectionState,
    FrozenDomainModel,
    PerformanceHorizon,
    ResolutionState,
)


class CalibrationDataQuality(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"


class CalibrationRunMode(str, Enum):
    STRESS = "stress"
    SYSTEMATIC = "systematic"
    PILOT = "pilot"
    HOLDOUT = "holdout"
    WALK_FORWARD = "walk_forward"


class ResearchFindingType(str, Enum):
    METRIC_NON_MONOTONIC = "metric_non_monotonic"
    FALSE_POSITIVE_PATTERN = "false_positive_pattern"
    FALSE_NEGATIVE_PATTERN = "false_negative_pattern"
    REGIME_DEPENDENCE = "regime_dependence"
    COVERAGE_ISSUE = "coverage_issue"
    VALUATION_INCREMENTAL_EFFECT = "valuation_incremental_effect"


class ResearchFindingStatus(str, Enum):
    OBSERVED = "observed"
    REQUIRES_VALIDATION = "requires_validation"
    VALIDATED = "validated"
    REJECTED = "rejected"
    CHANGE_CANDIDATE = "change_candidate"


class ResearchConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNRESOLVED = "unresolved"


class ResearchSignalLayer(str, Enum):
    QUANT = "quant"
    INVESTMENT_GRADE = "investment_grade"


class CalibrationLayer(str, Enum):
    QUANT = "quant"
    QUANT_CURRENT = "quant_current"
    QUANT_CURRENT_VALUATION = "quant_current_valuation"
    FULL_INVESTMENT_GRADE = "full_investment_grade"


class DateRange(FrozenDomainModel):
    start: date
    end: date

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.end < self.start:
            raise ValueError("date range end cannot precede start")
        return self


class LogicVersionSet(FrozenDomainModel):
    case: str
    case_version: str
    quant_engine_version: str
    current_engine_version: str | None = None
    valuation_version: str | None = None
    investment_grade_version: str | None = None


class CaseEvaluationHorizon(FrozenDomainModel):
    case: str
    primary_evaluation_horizon: PerformanceHorizon


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class CalibrationRun(FrozenDomainModel):
    run_id: str
    calibration_version: str
    git_commit: str
    created_at: datetime
    universe_version: str
    data_version: str
    start_date: date
    end_date: date
    included_cases: tuple[str, ...]
    logic_versions: tuple[LogicVersionSet, ...]
    performance_version: str
    benchmark_policy_version: str | None = None
    run_mode: CalibrationRunMode
    primary_evaluation_horizons: tuple[CaseEvaluationHorizon, ...]
    config_hash: str
    development_period: DateRange | None = None
    validation_period: DateRange | None = None
    holdout_period: DateRange | None = None
    notes: str | None = None

    def configuration_payload(self) -> dict[str, Any]:
        """Return execution inputs only; runtime identity and notes are excluded."""
        payload = self.model_dump(mode="json", exclude={
            "run_id", "git_commit", "created_at", "config_hash", "notes"
        })
        payload["included_cases"] = sorted(payload["included_cases"])
        payload["logic_versions"] = sorted(
            payload["logic_versions"], key=lambda item: item["case"]
        )
        payload["primary_evaluation_horizons"] = sorted(
            payload["primary_evaluation_horizons"], key=lambda item: item["case"]
        )
        return payload

    def expected_config_hash(self) -> str:
        return _canonical_hash(self.configuration_payload())

    @model_validator(mode="after")
    def validate_run(self) -> Self:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        if self.end_date < self.start_date:
            raise ValueError("calibration end_date cannot precede start_date")
        if len(self.included_cases) != len(set(self.included_cases)):
            raise ValueError("included cases must be unique")
        version_cases = [item.case for item in self.logic_versions]
        horizon_cases = [item.case for item in self.primary_evaluation_horizons]
        if len(version_cases) != len(set(version_cases)):
            raise ValueError("logic version cases must be unique")
        if len(horizon_cases) != len(set(horizon_cases)):
            raise ValueError("primary horizon cases must be unique")
        if set(version_cases) != set(self.included_cases):
            raise ValueError("every included case requires exactly one logic version set")
        if set(horizon_cases) != set(self.included_cases):
            raise ValueError("every included case requires a primary evaluation horizon")
        if self.config_hash != self.expected_config_hash():
            raise ValueError("config_hash does not match the reproducible run configuration")
        return self


def build_calibration_run(**values: Any) -> CalibrationRun:
    """Build a run with a deterministic hash independent of run id and creation time."""
    provisional = CalibrationRun.model_construct(config_hash="", **values)
    return CalibrationRun(config_hash=provisional.expected_config_hash(), **values)


class CalibrationRecord(FrozenDomainModel):
    record_id: str
    analysis_snapshot_id: str
    performance_snapshot_id: str
    company_id: str
    instrument_id: str
    ticker: str
    case: str
    case_version: str
    quant_engine_version: str
    current_engine_version: str | None = None
    valuation_version: str | None = None
    investment_grade_version: str | None = None
    analysis_as_of: datetime
    calibration_run_id: str
    performance_state: ResolutionState
    data_quality: CalibrationDataQuality
    regime_tag: str | None = None
    cohort_tags: tuple[str, ...] = ()
    is_boundary_sample: bool = False
    source_scope: str

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        if self.analysis_as_of.tzinfo is None or self.analysis_as_of.utcoffset() is None:
            raise ValueError("analysis_as_of must be timezone-aware")
        if len(self.cohort_tags) != len(set(self.cohort_tags)):
            raise ValueError("cohort tags must be unique")
        return self


class MetricResearchObservation(FrozenDomainModel):
    calibration_record_id: str
    analysis_snapshot_id: str
    case: str
    metric_key: str
    state: ResolutionState
    raw_value: float | str | bool | None = None
    normalized_value: float | str | bool | None = None
    metric_grade: str | None = None
    unit: str | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> Self:
        if self.state == ResolutionState.UNRESOLVED and any(
            value is not None
            for value in (self.raw_value, self.normalized_value, self.metric_grade)
        ):
            raise ValueError("unresolved research metric cannot contain values or grade")
        return self


class MetricCohortStatistics(FrozenDomainModel):
    case: str
    metric_key: str
    metric_grade: str
    horizon: PerformanceHorizon
    sample_count: int = Field(ge=0)
    mean_return: float | None = None
    median_return: float | None = None
    positive_return_rate: float | None = None
    median_max_drawdown: float | None = None
    median_alpha: float | None = None


class LayerCoverage(FrozenDomainModel):
    total_records: int = Field(ge=0)
    quant_resolved: int = Field(ge=0)
    current_resolved: int = Field(ge=0)
    valuation_resolved: int = Field(ge=0)
    narrative_resolved: int = Field(ge=0)
    full_investment_grade_resolved: int = Field(ge=0)


class LayerOutcomeStatistics(FrozenDomainModel):
    layer: CalibrationLayer
    eligible_record_count: int = Field(ge=0)
    layer_resolved_count: int = Field(ge=0)
    return_sample_count: int = Field(ge=0)
    mean_return: float | None = None
    median_return: float | None = None
    positive_return_rate: float | None = None


class ResearchScreen(FrozenDomainModel):
    layer: ResearchSignalLayer
    grades: frozenset[str]
    horizon: PerformanceHorizon
    maximum_return: float | None = None
    minimum_return: float | None = None

    @model_validator(mode="after")
    def validate_condition(self) -> Self:
        if not self.grades:
            raise ValueError("research screen requires at least one grade")
        if self.maximum_return is None and self.minimum_return is None:
            raise ValueError("research screen requires a return boundary")
        return self


class ResearchCandidate(FrozenDomainModel):
    calibration_record_id: str
    company_id: str
    ticker: str
    analysis_as_of: datetime
    case: str
    matched_grade: str
    horizon: PerformanceHorizon
    future_return: float
    metrics: tuple[MetricResearchObservation, ...]
    current_signal: DirectionState | None = None
    expectation_gap: str | None = None


class MetricVersionChange(FrozenDomainModel):
    metric_key: str
    previous_value: float | str | bool | None = None
    current_value: float | str | bool | None = None
    previous_grade: str | None = None
    current_grade: str | None = None


class LogicVersionComparison(FrozenDomainModel):
    company_id: str
    instrument_id: str
    analysis_as_of: datetime
    previous_record_id: str
    current_record_id: str
    previous_quant_version: str
    current_quant_version: str
    previous_quant_grade: str | None = None
    current_quant_grade: str | None = None
    metric_changes: tuple[MetricVersionChange, ...]
    coverage_changed: bool


class ResearchFinding(FrozenDomainModel):
    finding_id: str
    calibration_run_id: str
    case: str | None = None
    component: str
    finding_type: ResearchFindingType
    description: str
    evidence_summary: str
    sample_count: int = Field(ge=0)
    confidence_level: ResearchConfidence
    status: ResearchFindingStatus

    def policy_change(self) -> None:
        """Research evidence cannot directly mutate frozen investment policy."""
        raise RuntimeError("ResearchFinding requires ADR/design review and a new logic version")
