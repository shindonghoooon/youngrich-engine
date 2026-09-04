"""Explicit append-only repositories for Persistence Phase 1."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.persistence.mappers import (
    analysis_from_row,
    analysis_to_rows,
    company_from_row,
    company_to_row,
    exit_evidence_rows,
    instrument_from_row,
    instrument_to_row,
    kpi_definition_from_row,
    kpi_definition_to_row,
    kpi_observation_from_row,
    kpi_observation_to_row,
    price_from_row,
    price_to_row,
    source_from_row,
    source_to_row,
    thesis_from_row,
    thesis_to_row,
    valuation_assumption_from_row,
    valuation_assumption_to_row,
)
from engine.persistence.models import (
    AnalysisSnapshotRow,
    CompanyRow,
    CurrentTrendSignalRow,
    CurrentTrendSnapshotRow,
    InstrumentRow,
    InvestmentGradeAdjustmentRow,
    InvestmentGradeSnapshotRow,
    MetricResultRow,
    NarrativeAssessmentRow,
    NarrativeSnapshotRow,
    PriceSnapshotRow,
    QuantSnapshotRow,
    SourceReferenceRow,
    ThesisDefinitionRow,
    ThesisStatusSnapshotRow,
    TrackingKPIDefinitionRow,
    TrackingKPIObservationRow,
    ValuationAssumptionRow,
    ValuationSnapshotRow,
)
from engine.persistence.schemas import Company, Instrument, SourceReference
from engine.tracking_models import (
    AnalysisSnapshot,
    PriceSnapshot,
    ThesisDefinition,
    TrackingKPIDefinition,
    TrackingKPIObservation,
    ValuationAssumptionSet,
)


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _utc(value: datetime) -> datetime:
    _require_aware(value, "datetime")
    return value.astimezone(timezone.utc)


def _commit(session: Session, *rows: object) -> None:
    try:
        session.add_all(rows)
        session.commit()
    except Exception:
        session.rollback()
        raise


class IdentityRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_company(self, company: Company) -> None:
        _commit(self.session, company_to_row(company))

    def get_company(self, company_id: str) -> Company | None:
        row = self.session.get(CompanyRow, company_id)
        return company_from_row(row) if row else None

    def add_instrument(self, instrument: Instrument) -> None:
        if self.session.get(CompanyRow, instrument.company_id) is None:
            raise ValueError("instrument company_id does not exist")
        _commit(self.session, instrument_to_row(instrument))

    def get_instrument(self, instrument_id: str) -> Instrument | None:
        row = self.session.get(InstrumentRow, instrument_id)
        return instrument_from_row(row) if row else None

    def list_company_instruments(self, company_id: str) -> tuple[Instrument, ...]:
        rows = self.session.scalars(
            select(InstrumentRow)
            .where(InstrumentRow.company_id == company_id)
            .order_by(InstrumentRow.exchange, InstrumentRow.ticker)
        ).all()
        return tuple(instrument_from_row(row) for row in rows)


class SourceRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_source_reference(self, source: SourceReference) -> None:
        _commit(self.session, source_to_row(source))

    def get_source_reference(self, source_reference_id: str) -> SourceReference | None:
        row = self.session.get(SourceReferenceRow, source_reference_id)
        return source_from_row(row) if row else None


class PriceRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_price_snapshot(self, price: PriceSnapshot, *, instrument_id: str) -> None:
        instrument = self.session.get(InstrumentRow, instrument_id)
        if instrument is None:
            raise ValueError("instrument_id does not exist")
        if instrument.ticker != price.ticker:
            raise ValueError("price ticker must match instrument ticker")
        if price.company_id is not None and price.company_id != instrument.company_id:
            raise ValueError("price company_id must match instrument company_id")
        _commit(self.session, price_to_row(price, instrument_id))

    def get_price_snapshot(self, price_snapshot_id: str) -> PriceSnapshot | None:
        row = self.session.get(PriceSnapshotRow, price_snapshot_id)
        return price_from_row(row) if row else None

    def list_price_snapshots(self, instrument_id: str) -> tuple[PriceSnapshot, ...]:
        rows = self.session.scalars(
            select(PriceSnapshotRow)
            .where(PriceSnapshotRow.instrument_id == instrument_id)
            .order_by(PriceSnapshotRow.timestamp, PriceSnapshotRow.price_snapshot_id)
        ).all()
        return tuple(price_from_row(row) for row in rows)


class ValuationRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_valuation_assumption(
        self,
        assumption: ValuationAssumptionSet,
        *,
        valid_from: datetime,
        created_at: datetime,
        company_id: str | None = None,
        instrument_id: str | None = None,
    ) -> None:
        if company_id is None and instrument_id is None:
            raise ValueError("valuation assumption requires company or instrument scope")
        _require_aware(valid_from, "valid_from")
        _require_aware(created_at, "created_at")
        for evidence in assumption.exit_multiples:
            _require_aware(evidence.as_of, "exit multiple evidence as_of")
        row = valuation_assumption_to_row(
            assumption,
            company_id=company_id,
            instrument_id=instrument_id,
            valid_from=valid_from,
            created_at=created_at,
        )
        try:
            self.session.add(row)
            self.session.flush()
            self.session.add_all(exit_evidence_rows(assumption, row.valuation_assumption_id))
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def get_valuation_assumption(self, assumption_set_id: str, version: int) -> ValuationAssumptionSet | None:
        row = self.session.scalar(
            select(ValuationAssumptionRow).where(
                ValuationAssumptionRow.assumption_set_id == assumption_set_id,
                ValuationAssumptionRow.assumption_version == version,
            )
        )
        return valuation_assumption_from_row(row) if row else None

    def list_valuation_assumptions(self, assumption_set_id: str) -> tuple[ValuationAssumptionSet, ...]:
        rows = self.session.scalars(
            select(ValuationAssumptionRow)
            .where(ValuationAssumptionRow.assumption_set_id == assumption_set_id)
            .order_by(ValuationAssumptionRow.assumption_version)
        ).all()
        return tuple(valuation_assumption_from_row(row) for row in rows)


class ThesisRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_thesis_definition(
        self,
        thesis: ThesisDefinition,
        *,
        created_at: datetime,
        company_id: str | None = None,
        instrument_id: str | None = None,
        valid_to: datetime | None = None,
        why_now: str | None = None,
        why_this_company: str | None = None,
    ) -> None:
        if company_id is None and instrument_id is None:
            raise ValueError("thesis definition requires company or instrument scope")
        _require_aware(thesis.effective_from, "effective_from")
        _require_aware(created_at, "created_at")
        if valid_to is not None:
            _require_aware(valid_to, "valid_to")
            if valid_to <= thesis.effective_from:
                raise ValueError("valid_to must be later than effective_from")
        _commit(self.session, thesis_to_row(
            thesis,
            company_id=company_id,
            instrument_id=instrument_id,
            created_at=created_at,
            valid_to=valid_to,
            why_now=why_now,
            why_this_company=why_this_company,
        ))

    def get_active_thesis_definition(self, thesis_id: str, as_of: datetime) -> ThesisDefinition | None:
        _require_aware(as_of, "as_of")
        row = self.session.scalar(
            select(ThesisDefinitionRow)
            .where(
                ThesisDefinitionRow.thesis_id == thesis_id,
                ThesisDefinitionRow.valid_from <= as_of,
                (ThesisDefinitionRow.valid_to.is_(None) | (ThesisDefinitionRow.valid_to > as_of)),
            )
            .order_by(ThesisDefinitionRow.thesis_version.desc())
            .limit(1)
        )
        return thesis_from_row(row) if row else None

    def add_kpi_definition(
        self,
        definition: TrackingKPIDefinition,
        *,
        company_id: str | None = None,
        instrument_id: str | None = None,
        frequency: str | None = None,
    ) -> None:
        thesis = self.session.scalar(select(ThesisDefinitionRow).where(
            ThesisDefinitionRow.thesis_id == definition.thesis_id,
            ThesisDefinitionRow.thesis_version == definition.thesis_version,
        ))
        if thesis is None or thesis.kpi_set_version != definition.kpi_set_version:
            raise ValueError("KPI definition version must match a persisted thesis version")
        _commit(self.session, kpi_definition_to_row(
            definition,
            company_id=company_id,
            instrument_id=instrument_id,
            frequency=frequency,
        ))

    def list_kpi_definitions(self, thesis_id: str, kpi_set_version: int) -> tuple[TrackingKPIDefinition, ...]:
        rows = self.session.scalars(
            select(TrackingKPIDefinitionRow)
            .where(
                TrackingKPIDefinitionRow.thesis_id == thesis_id,
                TrackingKPIDefinitionRow.kpi_set_version == kpi_set_version,
            )
            .order_by(TrackingKPIDefinitionRow.kpi_key)
        ).all()
        return tuple(kpi_definition_from_row(row) for row in rows)

    def add_kpi_observation(
        self,
        observation: TrackingKPIObservation,
        *,
        created_at: datetime,
        company_id: str | None = None,
        instrument_id: str | None = None,
        analysis_snapshot_id: str | None = None,
        unit: str | None = None,
    ) -> None:
        _require_aware(created_at, "created_at")
        _require_aware(observation.available_at, "available_at")
        _require_aware(observation.as_of, "as_of")
        definition = self.session.scalar(select(TrackingKPIDefinitionRow).where(
            TrackingKPIDefinitionRow.kpi_definition_id == observation.kpi_definition_id,
            TrackingKPIDefinitionRow.kpi_set_version == observation.kpi_set_version,
        ))
        if definition is None:
            raise ValueError("KPI observation requires a matching persisted definition")
        if definition.thesis_version != observation.thesis_version or definition.kpi_key != observation.kpi_key:
            raise ValueError("KPI observation version/key mismatch")
        if analysis_snapshot_id is not None:
            analysis = self.session.get(AnalysisSnapshotRow, analysis_snapshot_id)
            if analysis is None:
                raise ValueError("analysis_snapshot_id does not exist")
            persisted_as_of = analysis.as_of
            if persisted_as_of.tzinfo is None:
                persisted_as_of = persisted_as_of.replace(tzinfo=timezone.utc)
            if _utc(observation.available_at) > _utc(persisted_as_of):
                raise ValueError("KPI observation available_at cannot exceed linked analysis as_of")
        _commit(self.session, kpi_observation_to_row(
            observation,
            company_id=company_id,
            instrument_id=instrument_id,
            created_at=created_at,
            analysis_snapshot_id=analysis_snapshot_id,
            unit=unit,
        ))

    def list_kpi_observations(self, kpi_definition_id: str) -> tuple[TrackingKPIObservation, ...]:
        rows = self.session.scalars(
            select(TrackingKPIObservationRow)
            .where(TrackingKPIObservationRow.kpi_definition_id == kpi_definition_id)
            .order_by(TrackingKPIObservationRow.period_end, TrackingKPIObservationRow.observation_id)
        ).all()
        return tuple(kpi_observation_from_row(row) for row in rows)


class AnalysisRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_analysis_snapshot(
        self,
        snapshot: AnalysisSnapshot,
        *,
        instrument_id: str,
        company_id: str,
        created_at: datetime,
        supersedes_snapshot_id: str | None = None,
        revision_reason: str | None = None,
    ) -> None:
        _require_aware(created_at, "created_at")
        _require_aware(snapshot.available_at, "available_at")
        _require_aware(snapshot.as_of, "as_of")
        for component in (
            snapshot.quant,
            snapshot.current_trend,
            snapshot.narrative,
            snapshot.thesis_status,
            snapshot.valuation,
            snapshot.investment_grade,
        ):
            if component is not None:
                _require_aware(component.available_at, "component available_at")
                _require_aware(component.as_of, "component as_of")
        instrument = self.session.get(InstrumentRow, instrument_id)
        if instrument is None or instrument.company_id != company_id:
            raise ValueError("analysis identity must reference a matching company/instrument")
        if instrument.ticker != snapshot.ticker:
            raise ValueError("analysis ticker must match instrument ticker")
        if supersedes_snapshot_id is None and revision_reason is not None:
            raise ValueError("revision_reason requires supersedes_snapshot_id")
        if supersedes_snapshot_id is not None:
            previous = self.session.get(AnalysisSnapshotRow, supersedes_snapshot_id)
            if previous is None:
                raise ValueError("superseded analysis snapshot does not exist")
            if previous.instrument_id != instrument_id or previous.company_id != company_id:
                raise ValueError("correction lineage must retain company/instrument identity")
            if not revision_reason or not revision_reason.strip():
                raise ValueError("correction requires a revision_reason")
        rows = analysis_to_rows(
            snapshot,
            instrument_id=instrument_id,
            company_id=company_id,
            created_at=created_at,
            supersedes_snapshot_id=supersedes_snapshot_id,
            revision_reason=revision_reason,
        )
        parent_types = (
            QuantSnapshotRow,
            CurrentTrendSnapshotRow,
            NarrativeSnapshotRow,
            ThesisStatusSnapshotRow,
            ValuationSnapshotRow,
            InvestmentGradeSnapshotRow,
        )
        leaf_types = (
            MetricResultRow,
            CurrentTrendSignalRow,
            NarrativeAssessmentRow,
            InvestmentGradeAdjustmentRow,
        )
        try:
            self.session.add(rows.root)
            self.session.flush()
            self.session.add_all(
                [row for row in rows.children if isinstance(row, parent_types)]
            )
            self.session.flush()
            self.session.add_all(
                [row for row in rows.children if isinstance(row, leaf_types)]
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def get_analysis_snapshot(self, snapshot_id: str) -> AnalysisSnapshot | None:
        row = self.session.get(AnalysisSnapshotRow, snapshot_id)
        return analysis_from_row(row) if row else None

    def list_analysis_snapshots(self, instrument_id: str) -> tuple[AnalysisSnapshot, ...]:
        rows = self.session.scalars(
            select(AnalysisSnapshotRow)
            .where(AnalysisSnapshotRow.instrument_id == instrument_id)
            .order_by(AnalysisSnapshotRow.as_of, AnalysisSnapshotRow.created_at, AnalysisSnapshotRow.snapshot_id)
        ).all()
        return tuple(analysis_from_row(row) for row in rows)

    def get_latest_analysis_snapshot(self, instrument_id: str) -> AnalysisSnapshot | None:
        row = self.session.scalar(
            select(AnalysisSnapshotRow)
            .where(AnalysisSnapshotRow.instrument_id == instrument_id)
            .order_by(AnalysisSnapshotRow.as_of.desc(), AnalysisSnapshotRow.created_at.desc())
            .limit(1)
        )
        return analysis_from_row(row) if row else None
