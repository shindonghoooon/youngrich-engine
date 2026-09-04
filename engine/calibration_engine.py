"""Thin, Case-agnostic join kernel for calibration research."""

from __future__ import annotations

from typing import Protocol

from engine.calibration_models import (
    CalibrationDataQuality,
    CalibrationRecord,
    CalibrationRun,
    LogicVersionSet,
)
from engine.tracking_models import PerformanceSnapshot


class QuantSnapshotLike(Protocol):
    model_version: str


class HistoricalAnalysisLike(Protocol):
    snapshot_id: str
    ticker: str
    case: object
    case_definition_version: str
    as_of: object
    quant: QuantSnapshotLike
    current_trend: object | None
    valuation: object | None
    investment_grade: object | None


def _value(value: object) -> str:
    return str(getattr(value, "value", value))


def _versions_for(run: CalibrationRun, case: str) -> LogicVersionSet:
    match = next((item for item in run.logic_versions if item.case == case), None)
    if match is None:
        raise ValueError(f"case {case!r} is not configured for calibration run")
    return match


def _valuation_version(valuation: object | None) -> str | None:
    if valuation is None:
        return None
    assumptions = getattr(valuation, "assumption_set")
    return f"{assumptions.assumption_set_id}:v{assumptions.version}"


def build_calibration_record(
    *,
    record_id: str,
    run: CalibrationRun,
    analysis: HistoricalAnalysisLike,
    performance: PerformanceSnapshot,
    company_id: str,
    instrument_id: str,
    data_quality: CalibrationDataQuality,
    source_scope: str,
    regime_tag: str | None = None,
    cohort_tags: tuple[str, ...] = (),
    is_boundary_sample: bool = False,
) -> CalibrationRecord:
    """Join immutable snapshots without copying metrics or future-return values."""
    case = _value(analysis.case)
    expected = _versions_for(run, case)
    if analysis.snapshot_id != performance.analysis_snapshot_id:
        raise ValueError("performance must reference the analysis snapshot")
    if analysis.ticker != performance.ticker:
        raise ValueError("analysis and performance ticker must match")
    if performance.instrument_id != instrument_id:
        raise ValueError("performance instrument must match CalibrationRecord instrument")
    if performance.evaluation_as_of < analysis.as_of:
        raise ValueError("performance evaluation cannot precede analysis as_of")
    if performance.calculation_version != run.performance_version:
        raise ValueError("performance version is incompatible with CalibrationRun")
    if analysis.case_definition_version != expected.case_version:
        raise ValueError("case version is incompatible with CalibrationRun")
    if analysis.quant.model_version != expected.quant_engine_version:
        raise ValueError("quant version is incompatible with CalibrationRun")

    current_version = (
        getattr(analysis.current_trend, "model_version")
        if analysis.current_trend is not None else None
    )
    valuation_version = _valuation_version(analysis.valuation)
    investment_version = (
        getattr(analysis.investment_grade, "model_version")
        if analysis.investment_grade is not None else None
    )
    for label, actual, configured in (
        ("current", current_version, expected.current_engine_version),
        ("valuation", valuation_version, expected.valuation_version),
        ("investment grade", investment_version, expected.investment_grade_version),
    ):
        if actual is not None and actual != configured:
            raise ValueError(f"{label} version is incompatible with CalibrationRun")

    return CalibrationRecord(
        record_id=record_id,
        analysis_snapshot_id=analysis.snapshot_id,
        performance_snapshot_id=performance.performance_snapshot_id,
        company_id=company_id,
        instrument_id=instrument_id,
        ticker=analysis.ticker,
        case=case,
        case_version=analysis.case_definition_version,
        quant_engine_version=analysis.quant.model_version,
        current_engine_version=current_version,
        valuation_version=valuation_version,
        investment_grade_version=investment_version,
        analysis_as_of=analysis.as_of,
        calibration_run_id=run.run_id,
        performance_state=performance.state,
        data_quality=data_quality,
        regime_tag=regime_tag,
        cohort_tags=cohort_tags,
        is_boundary_sample=is_boundary_sample,
        source_scope=source_scope,
    )
