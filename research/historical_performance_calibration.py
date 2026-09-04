"""Offline assembly for the outcome-aware Historical Stress Calibration v0.1."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from engine.case1_snapshot import WEIGHTS as CASE1_CORE_WEIGHTS
from engine.case2_policy import CASE2_CORE_WEIGHTS
from engine.performance_engine import build_performance_snapshot
from engine.tracking_models import (
    AnalysisCase,
    AnalysisSnapshot,
    BenchmarkAssignment,
    InvestmentGrade,
    InvestmentGradeSnapshot,
    MetricResult,
    PerformanceReturnType,
    PerformanceSnapshot,
    PriceBasis,
    PriceSnapshot,
    PriceType,
    QuantSnapshot,
    ResolutionState,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "performance_historical"
CALCULATION_VERSION = "historical-stress-calibration-v0.1"


class AnalysisInputState(str, Enum):
    COMPLETE = "COMPLETE"
    ANALYSIS_INPUT_INCOMPLETE = "ANALYSIS_INPUT_INCOMPLETE"


class HistoricalStressMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_id: str
    ticker: str
    company: str
    historical_case: AnalysisCase
    sample_role: str
    reporting_period_end: date
    information_available_at: datetime
    analysis_as_of: datetime
    analysis_input_state: AnalysisInputState
    canonical_investment_grade: InvestmentGrade | None = None
    canonical_grade_range: tuple[InvestmentGrade, ...] | None = None
    expectation_gap: str | None = None
    funding_stress: bool | None = None
    commercial_inflection: bool | None = None
    thesis_status: str | None = None
    price_basis: PriceBasis
    return_type: PerformanceReturnType
    currency: str
    adjustment_version: str


class HistoricalStressRecord(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    metadata: HistoricalStressMetadata
    analysis: AnalysisSnapshot
    performance: PerformanceSnapshot
    raw_fixture: dict


def _read_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _unresolved_quant(metadata: HistoricalStressMetadata) -> QuantSnapshot:
    weights = (CASE1_CORE_WEIGHTS if metadata.historical_case == AnalysisCase.CASE_1_PROFITABLE_GROWTH
               else CASE2_CORE_WEIGHTS)
    metrics = tuple(
        MetricResult(
            name=name,
            state=ResolutionState.UNRESOLVED,
            weight=weight,
            note="ANALYSIS_INPUT_INCOMPLETE: exact frozen historical metric input not recoverable",
        )
        for name, weight in weights.items()
    )
    return QuantSnapshot(
        snapshot_id=f"{metadata.sample_id}-quant",
        ticker=metadata.ticker,
        case=metadata.historical_case,
        model_version=CALCULATION_VERSION,
        metrics=metrics,
        state=ResolutionState.UNRESOLVED,
        coverage=0.0,
        provisional=True,
        period_end=metadata.reporting_period_end,
        available_at=metadata.information_available_at,
        as_of=metadata.analysis_as_of,
    )


def _canonical_grade(metadata: HistoricalStressMetadata) -> InvestmentGradeSnapshot | None:
    if metadata.canonical_investment_grade is None:
        return None
    return InvestmentGradeSnapshot(
        snapshot_id=f"{metadata.sample_id}-investment-grade",
        ticker=metadata.ticker,
        model_version=CALCULATION_VERSION,
        initial_valuation_grade=metadata.canonical_investment_grade,
        final_grade=metadata.canonical_investment_grade,
        rationale=("Canonical historical grade preserved by project instruction; detailed historical "
                   "Quant, Narrative, and Valuation inputs remain ANALYSIS_INPUT_INCOMPLETE."),
        period_end=metadata.reporting_period_end,
        available_at=metadata.information_available_at,
        as_of=metadata.analysis_as_of,
    )


def _price(item: dict, *, metadata: HistoricalStressMetadata, ticker: str,
           source_url: str, prefix: str, reference_timestamp: str | None) -> PriceSnapshot:
    timestamp = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
    identifier = f"{metadata.sample_id}-{prefix}-{timestamp.date().isoformat()}"
    if reference_timestamp == item["timestamp"]:
        identifier = f"{metadata.sample_id}-{prefix}-reference"
    return PriceSnapshot(
        price_snapshot_id=identifier,
        ticker=ticker,
        timestamp=timestamp,
        price=item["price"],
        currency=metadata.currency,
        source="Yahoo Finance Chart API offline fixture",
        price_type=PriceType.CLOSE,
        price_basis=metadata.price_basis,
        adjustment_version=metadata.adjustment_version,
        provider_reference=source_url,
        created_at=datetime(2026, 9, 4, 12, tzinfo=timezone.utc),
    )


def build_record(raw: dict) -> HistoricalStressRecord:
    metadata = HistoricalStressMetadata.model_validate(raw)
    reference = raw["reference_price"]
    reference_id = f"{metadata.sample_id}-stock-reference" if reference else None
    analysis = AnalysisSnapshot(
        snapshot_id=f"{metadata.sample_id}-analysis",
        ticker=metadata.ticker,
        company_name=metadata.company,
        case=metadata.historical_case,
        case_definition_version=CALCULATION_VERSION,
        quant=_unresolved_quant(metadata),
        investment_grade=_canonical_grade(metadata),
        reference_price_snapshot_id=reference_id,
        period_end=metadata.reporting_period_end,
        available_at=metadata.information_available_at,
        as_of=metadata.analysis_as_of,
    )
    stock_url = raw["price_source"]["stock_url"]
    stock_prices = tuple(
        _price(item, metadata=metadata, ticker=metadata.ticker, source_url=stock_url,
               prefix="stock", reference_timestamp=reference["timestamp"] if reference else None)
        for item in raw["stock_prices"]
    )
    benchmark = raw["benchmark_assignment"]
    benchmark_prices = tuple(
        _price(item, metadata=metadata, ticker=benchmark["ticker"], source_url=benchmark["source_url"],
               prefix="benchmark", reference_timestamp=benchmark["reference_timestamp"])
        for item in raw["benchmark_prices"]
    )
    assignment = BenchmarkAssignment(
        assignment_id=f"{metadata.sample_id}-benchmark-assignment",
        instrument_id=f"{metadata.sample_id}-instrument",
        benchmark_instrument_id="spy-instrument",
        version=benchmark["version"],
        valid_from=datetime.fromisoformat(benchmark["valid_from"].replace("Z", "+00:00")),
        rationale=benchmark["rationale"],
        created_at=datetime(2026, 9, 4, 12, tzinfo=timezone.utc),
    )
    evaluation_as_of = (datetime.fromisoformat(raw["evaluation_as_of"].replace("Z", "+00:00"))
                        if raw["evaluation_as_of"] else metadata.analysis_as_of + timedelta(days=366))
    performance = build_performance_snapshot(
        performance_snapshot_id=f"{metadata.sample_id}-performance-1y",
        analysis=analysis,
        instrument_id=f"{metadata.sample_id}-instrument",
        evaluation_as_of=evaluation_as_of,
        return_type=metadata.return_type,
        price_basis=metadata.price_basis,
        stock_prices=stock_prices,
        benchmark_assignment=assignment,
        benchmark_prices=benchmark_prices,
        benchmark_start_price_snapshot_id=(f"{metadata.sample_id}-benchmark-reference"
                                           if benchmark["reference_timestamp"] else None),
        created_at=datetime(2026, 9, 4, 12, tzinfo=timezone.utc),
    )
    return HistoricalStressRecord(metadata=metadata, analysis=analysis,
                                  performance=performance, raw_fixture=raw)


def load_historical_stress_records(root: Path = FIXTURE_ROOT) -> tuple[HistoricalStressRecord, ...]:
    manifest = _read_fixture(root / "manifest.json")
    return tuple(build_record(_read_fixture(root / item["path"])) for item in manifest["samples"])


def research_cohort_labels(
    records: tuple[HistoricalStressRecord, ...], field: str
) -> dict[str, str | None]:
    """Expose explicitly stored research labels without mutating analysis snapshots."""
    allowed = {"expectation_gap", "funding_stress", "commercial_inflection", "sample_role"}
    if field not in allowed:
        raise ValueError(f"unsupported historical research cohort field: {field}")
    labels: dict[str, str | None] = {}
    for record in records:
        value = getattr(record.metadata, field)
        if isinstance(value, bool):
            label = str(value).lower()
        elif field == "sample_role" and value == "SUPPORTING_BOUNDARY":
            label = "supporting_boundary"
        elif field == "sample_role":
            label = record.metadata.historical_case.value
        else:
            label = value
        labels[record.analysis.snapshot_id] = label
    return labels
