"""Persistence-facing identity and provenance contracts.

Calculation modules intentionally do not import these models.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


class PersistenceDomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Company(PersistenceDomainModel):
    company_id: str
    canonical_name: str
    country: str | None = None
    sector: str | None = None
    industry: str | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_created_at(self) -> Self:
        _require_aware(self.created_at, "created_at")
        return self


class Instrument(PersistenceDomainModel):
    instrument_id: str
    company_id: str
    ticker: str
    exchange: str
    currency: str = Field(min_length=3, max_length=3)
    security_type: str = "common_stock"
    is_primary_listing: bool = True
    active: bool = True
    valid_from: date | None = None
    valid_to: date | None = None

    @model_validator(mode="after")
    def validate_validity(self) -> Self:
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to cannot precede valid_from")
        return self


class SourceReference(PersistenceDomainModel):
    source_reference_id: str
    source_type: str
    reference: str
    filing_date: date | None = None
    period_end: date | None = None
    available_at: datetime
    retrieved_at: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        _require_aware(self.available_at, "available_at")
        if self.retrieved_at is not None:
            _require_aware(self.retrieved_at, "retrieved_at")
        return self


class MaterialEvent(PersistenceDomainModel):
    event_id: str
    instrument_id: str
    previous_snapshot_id: str | None = None
    current_snapshot_id: str
    category: str
    key: str
    previous_value: str | int | float | bool | None = None
    current_value: str | int | float | bool | None = None
    reason_type: str
    occurred_at: datetime
    detected_at: datetime

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        _require_aware(self.occurred_at, "occurred_at")
        _require_aware(self.detected_at, "detected_at")
        return self
