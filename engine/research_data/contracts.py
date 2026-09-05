"""Provider-neutral contracts for historical calibration inputs.

Provider clients stop at this boundary. Case adapters receive normalized, point-in-time
inputs and the generic calibration kernel remains unaware of SEC, DART, or price-source
semantics.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Generic, Protocol, TypeVar

from pydantic import model_validator

from engine.calibration_models import CalibrationDataQuality
from engine.tracking_models import FrozenDomainModel


ResultT = TypeVar("ResultT")
CaseInputT = TypeVar("CaseInputT")
PriceOutputT = TypeVar("PriceOutputT")


class ResearchDataFailureReason(str, Enum):
    UNIVERSE_MEMBERSHIP_UNAVAILABLE = "universe_membership_unavailable"
    FILING_UNAVAILABLE = "filing_unavailable"
    SHARES_UNAVAILABLE = "shares_unavailable"
    FINANCIAL_NORMALIZATION_FAILURE = "financial_normalization_failure"
    PRICE_UNAVAILABLE = "price_unavailable"
    CORPORATE_ACTION_UNSAFE = "corporate_action_unsafe"
    DELISTED_PAYOFF_UNRESOLVED = "delisted_payoff_unresolved"
    SOURCE_ACCESS = "source_access"
    OTHER = "other"


class SourceReference(FrozenDomainModel):
    provider: str
    role: str
    source_version: str
    url: str
    retrieved_at: datetime
    note: str | None = None

    @model_validator(mode="after")
    def validate_timestamp(self) -> "SourceReference":
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        return self


class ResearchDataFailure(FrozenDomainModel):
    reason: ResearchDataFailureReason
    stage: str
    detail: str


class ResearchDataResult(FrozenDomainModel, Generic[ResultT]):
    """Explicitly resolved, partial, or unresolved provider output."""

    quality: CalibrationDataQuality
    value: ResultT | None = None
    failures: tuple[ResearchDataFailure, ...] = ()
    sources: tuple[SourceReference, ...] = ()

    @model_validator(mode="after")
    def validate_resolution(self) -> "ResearchDataResult[ResultT]":
        if self.quality == CalibrationDataQuality.COMPLETE:
            if self.value is None:
                raise ValueError("complete research data requires a value")
            if self.failures:
                raise ValueError("complete research data cannot contain failures")
        elif self.quality == CalibrationDataQuality.PARTIAL:
            if self.value is None or not self.failures:
                raise ValueError("partial research data requires a value and failures")
        elif self.value is not None or not self.failures:
            raise ValueError("unresolved research data requires failures and no value")
        return self


class HistoricalSecurityCandidate(FrozenDomainModel):
    """Security-level identity whose membership is valid at one anchor date."""

    permanent_id: str
    company_id: str
    instrument_id: str
    ticker: str
    exchange: str
    anchor_date: date
    listing_start: date | None = None
    listing_end: date | None = None

    @model_validator(mode="after")
    def validate_membership_dates(self) -> "HistoricalSecurityCandidate":
        if self.listing_start is not None and self.listing_start > self.anchor_date:
            raise ValueError("listing_start cannot follow anchor_date")
        if self.listing_end is not None and self.listing_end < self.anchor_date:
            raise ValueError("listing_end cannot precede anchor_date")
        return self


class HistoricalUniverseSnapshot(FrozenDomainModel):
    anchor_date: date
    universe_version: str
    candidates: tuple[HistoricalSecurityCandidate, ...]

    @model_validator(mode="after")
    def validate_candidates(self) -> "HistoricalUniverseSnapshot":
        identities = [item.permanent_id for item in self.candidates]
        if len(identities) != len(set(identities)):
            raise ValueError("historical universe permanent identities must be unique")
        if any(item.anchor_date != self.anchor_date for item in self.candidates):
            raise ValueError("every candidate must belong to the universe anchor date")
        return self


class HistoricalInputEnvelope(FrozenDomainModel, Generic[CaseInputT]):
    """Normalized Case input with its independent PIT timestamps preserved."""

    permanent_id: str
    case: str
    period_end: date
    available_at: datetime
    analysis_as_of: datetime
    normalized_input: CaseInputT

    @model_validator(mode="after")
    def validate_point_in_time(self) -> "HistoricalInputEnvelope[CaseInputT]":
        if self.available_at.tzinfo is None or self.available_at.utcoffset() is None:
            raise ValueError("available_at must be timezone-aware")
        if self.analysis_as_of.tzinfo is None or self.analysis_as_of.utcoffset() is None:
            raise ValueError("analysis_as_of must be timezone-aware")
        if self.available_at > self.analysis_as_of:
            raise ValueError("available_at cannot be later than analysis_as_of")
        if self.period_end > self.analysis_as_of.date():
            raise ValueError("period_end cannot be later than analysis_as_of")
        return self


class HistoricalUniverseSource(Protocol):
    provider_name: str
    source_version: str

    def universe_as_of(
        self,
        anchor_date: date,
    ) -> ResearchDataResult[HistoricalUniverseSnapshot]: ...


class HistoricalFilingSource(Protocol, Generic[CaseInputT]):
    provider_name: str
    source_version: str

    def normalized_case_input(
        self,
        candidate: HistoricalSecurityCandidate,
        *,
        case: str,
        analysis_as_of: datetime,
    ) -> ResearchDataResult[HistoricalInputEnvelope[CaseInputT]]: ...


class HistoricalPriceSource(Protocol, Generic[PriceOutputT]):
    provider_name: str
    source_version: str

    def adjusted_prices(
        self,
        candidate: HistoricalSecurityCandidate,
        *,
        start: date,
        end: date,
    ) -> ResearchDataResult[PriceOutputT]: ...
