"""Adapters from historical inputs to existing frozen Case analysis paths."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, Protocol, TypeVar

from pydantic import model_validator

from engine.calibration_engine import HistoricalAnalysisLike
from engine.case1_snapshot import build_case1_snapshot, validate_case1_core_metrics
from engine.case2_analysis import Case2AnalysisInput, build_case2_analysis
from engine.case2_policy import EligibilityState
from engine.case2_quant import Case2QuantInput, build_case2_quant
from engine.financials import FinancialHistory
from engine.models import CapitalModel
from engine.tracking_models import (
    AnalysisCase,
    AnalysisSnapshot,
    FrozenDomainModel,
    MetricResult,
    QuantSnapshot,
    ResolutionState,
)


InputT = TypeVar("InputT")


class CaseBacktestAdapter(Protocol, Generic[InputT]):
    """Case-specific calculation boundary; fetching never belongs here."""

    case: str
    logic_version: str

    def is_eligible(self, inputs: InputT, as_of: datetime) -> bool: ...

    def evaluate(self, inputs: InputT, as_of: datetime) -> HistoricalAnalysisLike: ...


def evaluate_with_adapter(
    adapter: CaseBacktestAdapter[InputT],
    inputs: InputT,
    *,
    as_of: datetime,
) -> HistoricalAnalysisLike:
    """Run any structurally compatible adapter without Case-specific branching."""
    if not adapter.is_eligible(inputs, as_of):
        raise ValueError(f"input is not eligible for adapter {adapter.case}")
    return adapter.evaluate(inputs, as_of)


class Case1BacktestInput(FrozenDomainModel):
    snapshot_id: str
    quant_snapshot_id: str
    history: FinancialHistory
    capital_model: CapitalModel
    available_at: datetime
    as_of: datetime

    @model_validator(mode="after")
    def validate_timing(self) -> "Case1BacktestInput":
        if self.available_at > self.as_of:
            raise ValueError("available_at cannot be later than as_of")
        return self


class Case1BacktestAdapter:
    case = AnalysisCase.CASE_1_PROFITABLE_GROWTH.value
    logic_version = "case1-v1-frozen"
    quant_engine_version = "case1-quant-v1-frozen"

    def is_eligible(self, inputs: Case1BacktestInput, as_of: datetime) -> bool:
        latest = inputs.history.periods[-1]
        return (
            as_of == inputs.as_of
            and inputs.available_at <= as_of
            and len(inputs.history.periods) >= 4
            and latest.fiscal_period_end <= as_of.date()
            and latest.operating_income > 0
            and latest.net_income_consolidated > 0
        )

    def evaluate(
        self,
        inputs: Case1BacktestInput,
        as_of: datetime,
    ) -> AnalysisSnapshot:
        if as_of != inputs.as_of:
            raise ValueError("adapter as_of must match the versioned Case 1 input")
        existing = build_case1_snapshot(inputs.history, inputs.capital_model)
        metrics = tuple(
            MetricResult(
                name=metric.name,
                state=(
                    ResolutionState.RESOLVED
                    if metric.value is not None and metric.grade is not None
                    else ResolutionState.UNRESOLVED
                ),
                value=(
                    metric.value
                    if metric.value is not None and metric.grade is not None
                    else None
                ),
                unit=metric.unit,
                grade=metric.grade,
                trend=metric.trend,
                weight=metric.weight,
                supporting_tags=(
                    (metric.supporting_tag,) if metric.supporting_tag else ()
                ),
                note=metric.note,
            )
            for metric in existing.metrics
        )
        validate_case1_core_metrics(metrics)
        resolved_count = sum(
            metric.state == ResolutionState.RESOLVED for metric in metrics
        )
        state = (
            ResolutionState.RESOLVED
            if resolved_count == len(metrics)
            else ResolutionState.UNRESOLVED
        )
        latest = inputs.history.periods[-1]
        quant = QuantSnapshot(
            snapshot_id=inputs.quant_snapshot_id,
            ticker=inputs.history.ticker,
            case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
            model_version=self.quant_engine_version,
            period_end=latest.fiscal_period_end,
            available_at=inputs.available_at,
            as_of=as_of,
            metrics=metrics,
            state=state,
            score=existing.quant_score if state == ResolutionState.RESOLVED else None,
            uncapped_grade=(
                existing.quant_grade if state == ResolutionState.RESOLVED else None
            ),
            grade=existing.quant_grade if state == ResolutionState.RESOLVED else None,
            coverage=resolved_count / len(metrics),
            provisional=state == ResolutionState.UNRESOLVED,
        )
        return AnalysisSnapshot(
            snapshot_id=inputs.snapshot_id,
            ticker=inputs.history.ticker,
            company_name=inputs.history.company_name,
            case=AnalysisCase.CASE_1_PROFITABLE_GROWTH,
            case_definition_version=self.logic_version,
            capital_model=inputs.capital_model,
            period_end=latest.fiscal_period_end,
            available_at=inputs.available_at,
            as_of=as_of,
            quant=quant,
        )


class Case2BacktestAdapter:
    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH.value
    logic_version = "case2-v1-frozen"

    def is_eligible(self, inputs: Case2AnalysisInput, as_of: datetime) -> bool:
        return (
            inputs.available_at <= as_of
            and inputs.as_of == as_of
            and build_case2_quant(inputs.quant).eligibility == EligibilityState.ELIGIBLE
        )

    def evaluate(
        self,
        inputs: Case2AnalysisInput,
        as_of: datetime,
    ) -> AnalysisSnapshot:
        if as_of != inputs.as_of:
            raise ValueError("adapter as_of must match the versioned Case 2 input")
        return build_case2_analysis(inputs)


class Case2QuantOnlyAnalysis(FrozenDomainModel):
    """Minimal historical-analysis shape for Quant-only calibration."""

    snapshot_id: str
    ticker: str
    case: AnalysisCase = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH
    case_definition_version: str = "case2-v1-frozen"
    as_of: datetime
    quant: QuantSnapshot
    current_trend: None = None
    valuation: None = None
    investment_grade: None = None


class Case2QuantBacktestAdapter:
    """Run frozen Case 2 Quant without Narrative, Current, Valuation, price, or IG."""

    case = AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH.value
    logic_version = "case2-v1-frozen"

    def is_eligible(self, inputs: Case2QuantInput, as_of: datetime) -> bool:
        return (
            inputs.available_at <= as_of
            and inputs.as_of == as_of
            and build_case2_quant(inputs).eligibility == EligibilityState.ELIGIBLE
        )

    def evaluate(
        self,
        inputs: Case2QuantInput,
        as_of: datetime,
    ) -> Case2QuantOnlyAnalysis:
        if as_of != inputs.as_of:
            raise ValueError("adapter as_of must match the versioned Case 2 Quant input")
        result = build_case2_quant(inputs)
        return Case2QuantOnlyAnalysis(
            snapshot_id=f"{inputs.snapshot_id}-analysis",
            ticker=inputs.ticker,
            as_of=as_of,
            quant=result.snapshot,
        )
