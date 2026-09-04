"""SQLAlchemy 2.x schema for append-oriented investment history."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class ImmutableRecordError(RuntimeError):
    pass


class UTCDateTime(TypeDecorator[datetime]):
    """Store UTC instants portably and always return timezone-aware UTC values."""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=dialect.name == "postgresql"))

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("persistent datetime must be timezone-aware")
        normalized = value.astimezone(timezone.utc)
        if dialect.name == "sqlite":
            return normalized.replace(tzinfo=None)
        return normalized

    def process_result_value(self, value: datetime | None, _dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class CompanyRow(Base):
    __tablename__ = "companies"
    company_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(250), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100))
    sector: Mapped[str | None] = mapped_column(String(150))
    industry: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class InstrumentRow(Base):
    __tablename__ = "instruments"
    __table_args__ = (UniqueConstraint("exchange", "ticker", name="uq_instrument_exchange_ticker"),)
    instrument_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.company_id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    security_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_primary_listing: Mapped[bool] = mapped_column(Boolean, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


class SourceReferenceRow(Base):
    __tablename__ = "source_references"
    source_reference_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    reference: Mapped[str] = mapped_column(Text, nullable=False)
    filing_date: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    retrieved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    notes: Mapped[str | None] = mapped_column(Text)


class AnalysisSnapshotRow(Base):
    __tablename__ = "analysis_snapshots"
    snapshot_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.instrument_id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.company_id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(50), nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    as_of: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    case: Mapped[str] = mapped_column(String(80), nullable=False)
    case_version: Mapped[str] = mapped_column(String(80), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(80), nullable=False)
    price_reference_id: Mapped[str | None] = mapped_column(String(120))
    supersedes_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id"))
    revision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class QuantSnapshotRow(Base):
    __tablename__ = "quant_snapshots"
    snapshot_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_snapshot_id: Mapped[str] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id", ondelete="CASCADE"), unique=True, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    raw_score: Mapped[float | None] = mapped_column(Float)
    final_score: Mapped[float | None] = mapped_column(Float)
    raw_grade: Mapped[str | None] = mapped_column(String(20))
    final_grade: Mapped[str | None] = mapped_column(String(20))
    coverage: Mapped[float] = mapped_column(Float, nullable=False)
    provisional: Mapped[bool] = mapped_column(Boolean, nullable=False)
    resolution_state: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class MetricResultRow(Base):
    __tablename__ = "metric_results"
    __table_args__ = (UniqueConstraint("quant_snapshot_id", "metric_key", name="uq_metric_quant_key"),)
    metric_result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quant_snapshot_id: Mapped[str] = mapped_column(ForeignKey("quant_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_key: Mapped[str] = mapped_column(String(150), nullable=False)
    raw_value: Mapped[Any | None] = mapped_column(JSON)
    normalized_value: Mapped[Any | None] = mapped_column(JSON)
    unit: Mapped[str | None] = mapped_column(String(40))
    grade: Mapped[str | None] = mapped_column(String(20))
    resolution_state: Mapped[str] = mapped_column(String(30), nullable=False)
    source_period: Mapped[date] = mapped_column(Date, nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(80), nullable=False)
    normalization_notes: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class CurrentTrendSnapshotRow(Base):
    __tablename__ = "current_trend_snapshots"
    snapshot_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_snapshot_id: Mapped[str] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id", ondelete="CASCADE"), unique=True, nullable=False)
    overall_state: Mapped[str] = mapped_column(String(40), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    comparison_period: Mapped[date] = mapped_column(Date, nullable=False)
    funding_stress: Mapped[bool] = mapped_column(Boolean, nullable=False)
    commercial_inflection: Mapped[bool] = mapped_column(Boolean, nullable=False)
    commercial_deterioration: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class CurrentTrendSignalRow(Base):
    __tablename__ = "current_trend_signals"
    __table_args__ = (UniqueConstraint("current_trend_snapshot_id", "signal_key", name="uq_current_signal_key"),)
    current_trend_signal_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    current_trend_snapshot_id: Mapped[str] = mapped_column(ForeignKey("current_trend_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_key: Mapped[str] = mapped_column(String(150), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    observation: Mapped[str | None] = mapped_column(Text)


class NarrativeSnapshotRow(Base):
    __tablename__ = "narrative_snapshots"
    snapshot_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_snapshot_id: Mapped[str] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id", ondelete="CASCADE"), unique=True, nullable=False)
    narrative_version: Mapped[str] = mapped_column(String(80), nullable=False)
    thesis_id: Mapped[str] = mapped_column(String(120), nullable=False)
    thesis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_set_version: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_state: Mapped[str] = mapped_column(String(40), nullable=False)
    narrative_gate: Mapped[str | None] = mapped_column(String(40))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class NarrativeAssessmentRow(Base):
    __tablename__ = "narrative_assessments"
    __table_args__ = (UniqueConstraint("narrative_snapshot_id", "dimension", name="uq_narrative_dimension"),)
    narrative_assessment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    narrative_snapshot_id: Mapped[str] = mapped_column(ForeignKey("narrative_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    dimension: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class ThesisStatusSnapshotRow(Base):
    __tablename__ = "thesis_status_snapshots"
    __table_args__ = (CheckConstraint("lower(status) <> 'stable'", name="ck_thesis_status_not_stable"),)
    snapshot_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_snapshot_id: Mapped[str] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id", ondelete="CASCADE"), unique=True, nullable=False)
    thesis_id: Mapped[str] = mapped_column(String(120), nullable=False)
    thesis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_set_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    breaker_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    observation_ids: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ValuationAssumptionRow(Base):
    __tablename__ = "valuation_assumptions"
    __table_args__ = (UniqueConstraint("assumption_set_id", "assumption_version", name="uq_valuation_assumption_version"),)
    valuation_assumption_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assumption_set_id: Mapped[str] = mapped_column(String(120), nullable=False)
    assumption_version: Mapped[int] = mapped_column(Integer, nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.company_id"))
    instrument_id: Mapped[str | None] = mapped_column(ForeignKey("instruments.instrument_id"))
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    horizon_years: Mapped[int] = mapped_column(Integer, nullable=False)
    required_return: Mapped[float] = mapped_column(Float, nullable=False)
    terminal_stage: Mapped[str] = mapped_column(String(40), nullable=False)
    primary_metric: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    plausible_growth_low: Mapped[float | None] = mapped_column(Float)
    plausible_growth_high: Mapped[float | None] = mapped_column(Float)
    expected_dilution: Mapped[float | None] = mapped_column(Float)
    target_gross_margin: Mapped[float | None] = mapped_column(Float)
    target_operating_margin: Mapped[float | None] = mapped_column(Float)
    terminal_net_debt: Mapped[float | None] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ExitMultipleEvidenceRow(Base):
    __tablename__ = "exit_multiple_evidence"
    __table_args__ = (UniqueConstraint("valuation_assumption_id", "band", name="uq_exit_evidence_band"),)
    evidence_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    valuation_assumption_id: Mapped[int] = mapped_column(ForeignKey("valuation_assumptions.valuation_assumption_id", ondelete="CASCADE"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    as_of: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    valuation_metric: Mapped[str] = mapped_column(String(40), nullable=False)
    band: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_low: Mapped[float | None] = mapped_column(Float)
    observed_high: Mapped[float | None] = mapped_column(Float)
    reference_value: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ValuationSnapshotRow(Base):
    __tablename__ = "valuation_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["assumption_set_id", "assumption_version"],
            ["valuation_assumptions.assumption_set_id", "valuation_assumptions.assumption_version"],
            name="fk_valuation_snapshot_assumption_version",
        ),
    )
    snapshot_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_snapshot_id: Mapped[str] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id", ondelete="CASCADE"), unique=True, nullable=False)
    assumption_set_id: Mapped[str] = mapped_column(String(120), nullable=False)
    assumption_version: Mapped[int] = mapped_column(Integer, nullable=False)
    required_return: Mapped[float] = mapped_column(Float, nullable=False)
    horizon_years: Mapped[int] = mapped_column(Integer, nullable=False)
    terminal_stage: Mapped[str] = mapped_column(String(40), nullable=False)
    expectation_gap: Mapped[str] = mapped_column(String(40), nullable=False)
    bear_value: Mapped[float | None] = mapped_column(Float)
    base_value: Mapped[float | None] = mapped_column(Float)
    bull_value: Mapped[float | None] = mapped_column(Float)
    downside_severity: Mapped[str | None] = mapped_column(String(80))
    upside_optionality: Mapped[str | None] = mapped_column(String(80))
    asymmetry_type: Mapped[str] = mapped_column(String(40), nullable=False)
    valuation_confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    market_price_reference: Mapped[str | None] = mapped_column(String(120))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class InvestmentGradeSnapshotRow(Base):
    __tablename__ = "investment_grade_snapshots"
    snapshot_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_snapshot_id: Mapped[str] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id", ondelete="CASCADE"), unique=True, nullable=False)
    initial_grade: Mapped[str] = mapped_column(String(20), nullable=False)
    final_grade: Mapped[str] = mapped_column(String(20), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class InvestmentGradeAdjustmentRow(Base):
    __tablename__ = "investment_grade_adjustments"
    __table_args__ = (UniqueConstraint("investment_grade_snapshot_id", "sequence", name="uq_grade_adjustment_sequence"),)
    investment_grade_adjustment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investment_grade_snapshot_id: Mapped[str] = mapped_column(ForeignKey("investment_grade_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    adjustment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    trigger: Mapped[str] = mapped_column(String(60), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    maximum_grade: Mapped[str | None] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class PriceSnapshotRow(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (UniqueConstraint("instrument_id", "timestamp", "source", "price_type", name="uq_price_import_key"), CheckConstraint("price > 0", name="ck_price_positive"))
    price_snapshot_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.instrument_id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    market_cap: Mapped[float | None] = mapped_column(Float)
    enterprise_value: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(250), nullable=False)
    price_type: Mapped[str] = mapped_column(String(30), nullable=False)
    analysis_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ThesisDefinitionRow(Base):
    __tablename__ = "thesis_definitions"
    __table_args__ = (UniqueConstraint("thesis_id", "thesis_version", name="uq_thesis_version"),)
    thesis_definition_row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thesis_id: Mapped[str] = mapped_column(String(120), nullable=False)
    thesis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.company_id"))
    instrument_id: Mapped[str | None] = mapped_column(ForeignKey("instruments.instrument_id"))
    case: Mapped[str] = mapped_column(String(80), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(UTCDateTime())
    core_thesis: Mapped[str] = mapped_column(Text, nullable=False)
    why_now: Mapped[str | None] = mapped_column(Text)
    why_this_company: Mapped[str | None] = mapped_column(Text)
    failure_modes: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    kpi_set_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class TrackingKPIDefinitionRow(Base):
    __tablename__ = "tracking_kpi_definitions"
    __table_args__ = (UniqueConstraint("kpi_definition_id", "kpi_set_version", name="uq_kpi_definition_version"),)
    tracking_kpi_definition_row_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kpi_definition_id: Mapped[str] = mapped_column(String(120), nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.company_id"))
    instrument_id: Mapped[str | None] = mapped_column(ForeignKey("instruments.instrument_id"))
    thesis_id: Mapped[str] = mapped_column(String(120), nullable=False)
    thesis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_set_version: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    primary_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    direction: Mapped[str] = mapped_column(String(40), nullable=False)
    frequency: Mapped[str | None] = mapped_column(String(60))
    source_type: Mapped[str] = mapped_column(String(120), nullable=False)
    breaker_rule: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class TrackingKPIObservationRow(Base):
    __tablename__ = "tracking_kpi_observations"
    observation_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    kpi_definition_id: Mapped[str] = mapped_column(String(120), nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.company_id"))
    instrument_id: Mapped[str | None] = mapped_column(ForeignKey("instruments.instrument_id"))
    analysis_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id"))
    kpi_key: Mapped[str] = mapped_column(String(120), nullable=False)
    thesis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_set_version: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    as_of: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    resolution_state: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[Any | None] = mapped_column(JSON)
    unit: Mapped[str | None] = mapped_column(String(40))
    source_reference: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class MaterialEventRow(Base):
    __tablename__ = "material_events"
    event_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.instrument_id"), nullable=False)
    previous_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id"))
    current_snapshot_id: Mapped[str] = mapped_column(ForeignKey("analysis_snapshots.snapshot_id"), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    key: Mapped[str] = mapped_column(String(150), nullable=False)
    previous_value: Mapped[Any | None] = mapped_column(JSON)
    current_value: Mapped[Any | None] = mapped_column(JSON)
    reason_type: Mapped[str] = mapped_column(String(80), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


_IMMUTABLE_ROWS = (
    SourceReferenceRow, AnalysisSnapshotRow, QuantSnapshotRow, MetricResultRow,
    CurrentTrendSnapshotRow, CurrentTrendSignalRow, NarrativeSnapshotRow,
    NarrativeAssessmentRow, ThesisStatusSnapshotRow, ValuationAssumptionRow,
    ExitMultipleEvidenceRow, ValuationSnapshotRow, InvestmentGradeSnapshotRow,
    InvestmentGradeAdjustmentRow, PriceSnapshotRow, ThesisDefinitionRow,
    TrackingKPIDefinitionRow, TrackingKPIObservationRow, MaterialEventRow,
)


def _reject_mutation(_mapper, _connection, target) -> None:
    raise ImmutableRecordError(
        f"{type(target).__name__} is append-only; create a new version or correction"
    )


for _row_type in _IMMUTABLE_ROWS:
    event.listen(_row_type, "before_update", _reject_mutation)
    event.listen(_row_type, "before_delete", _reject_mutation)
