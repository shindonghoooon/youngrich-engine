"""Persistent membership lifecycle, independent of analysis and decision grade."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from hashlib import sha256

from pydantic import ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.persistence.models import AnalysisSnapshotRow, WatchlistMembershipRow
from engine.persistence.repositories import AnalysisRepository, IdentityRepository
from engine.persistence.schemas import Instrument
from engine.tracking_models import AnalysisSnapshot, FrozenDomainModel


class MembershipStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class WatchlistMembership(FrozenDomainModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    membership_id: str
    company_id: str
    instrument_id: str
    status: MembershipStatus
    tracking_started_at: datetime
    tracking_stopped_at: datetime | None
    reference_analysis_snapshot_id: str | None
    created_at: datetime
    registration_source: str


class ActiveWatchlistEntry(FrozenDomainModel):
    membership: WatchlistMembership
    instrument: Instrument
    reference_analysis: AnalysisSnapshot | None
    latest_analysis: AnalysisSnapshot | None


class WatchlistRepository:
    def __init__(self, session: Session):
        self.session = session

    def _row(self, instrument_id: str) -> WatchlistMembershipRow | None:
        return self.session.scalar(select(WatchlistMembershipRow).where(
            WatchlistMembershipRow.instrument_id == instrument_id
        ))

    def get(self, instrument_id: str) -> WatchlistMembership | None:
        row = self._row(instrument_id)
        return WatchlistMembership.model_validate(row) if row else None

    def add(self, instrument_id: str, *, at: datetime,
            reference_analysis_snapshot_id: str | None = None,
            registration_source: str = "manual") -> WatchlistMembership:
        self._validate_time(at)
        instrument = IdentityRepository(self.session).get_instrument(instrument_id)
        if instrument is None:
            raise ValueError("instrument must already exist")
        if reference_analysis_snapshot_id is not None:
            analysis = self.session.get(AnalysisSnapshotRow, reference_analysis_snapshot_id)
            if analysis is None or analysis.instrument_id != instrument_id:
                raise ValueError("reference analysis must belong to instrument")
            if analysis.as_of > at:
                raise ValueError("registration cannot precede reference analysis")
        row = self._row(instrument_id)
        if row is None:
            row = WatchlistMembershipRow(
                membership_id="watch-" + sha256(instrument_id.encode()).hexdigest(),
                company_id=instrument.company_id, instrument_id=instrument_id,
                status=MembershipStatus.ACTIVE.value, tracking_started_at=at,
                tracking_stopped_at=None, reference_analysis_snapshot_id=reference_analysis_snapshot_id,
                created_at=at, registration_source=registration_source,
            )
            self.session.add(row)
        elif row.status == MembershipStatus.INACTIVE.value:
            if at < row.tracking_stopped_at:
                raise ValueError("reactivation cannot precede deactivation")
            row.status = MembershipStatus.ACTIVE.value
            row.tracking_started_at = at
            row.tracking_stopped_at = None
            row.registration_source = registration_source
            if reference_analysis_snapshot_id is not None:
                row.reference_analysis_snapshot_id = reference_analysis_snapshot_id
        # An already-active add is a no-op, including its original reference.
        self.session.commit()
        return WatchlistMembership.model_validate(row)

    def deactivate(self, instrument_id: str, *, at: datetime) -> WatchlistMembership:
        self._validate_time(at)
        row = self._row(instrument_id)
        if row is None:
            raise ValueError("membership does not exist")
        if row.status == MembershipStatus.ACTIVE.value:
            if at < row.tracking_started_at:
                raise ValueError("deactivation cannot precede activation")
            row.status = MembershipStatus.INACTIVE.value
            row.tracking_stopped_at = at
            self.session.commit()
        return WatchlistMembership.model_validate(row)

    def list_active_watchlist(self) -> tuple[ActiveWatchlistEntry, ...]:
        identities, analyses = IdentityRepository(self.session), AnalysisRepository(self.session)
        rows = self.session.scalars(select(WatchlistMembershipRow).where(
            WatchlistMembershipRow.status == MembershipStatus.ACTIVE.value
        ).order_by(WatchlistMembershipRow.created_at, WatchlistMembershipRow.instrument_id)).all()
        return tuple(ActiveWatchlistEntry(
            membership=WatchlistMembership.model_validate(row),
            instrument=identities.get_instrument(row.instrument_id),
            reference_analysis=analyses.get_analysis_snapshot(row.reference_analysis_snapshot_id)
                if row.reference_analysis_snapshot_id else None,
            latest_analysis=analyses.get_latest_analysis_snapshot(row.instrument_id),
        ) for row in rows)

    @staticmethod
    def _validate_time(at: datetime) -> None:
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("membership timestamp must be timezone-aware")
