from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from engine.financials import SourceMetadata, UnitScale


class CurrentFinancialPeriod(BaseModel):
    period_end: date
    period_type: Literal["quarter", "ytd", "ttm"]
    revenue: float | None = None
    operating_income: float | None = None
    net_income_consolidated: float | None = None
    cfo: float | None = None
    capex: float | None = Field(default=None, ge=0)
    cash: float | None = Field(default=None, ge=0)
    total_debt: float | None = Field(default=None, ge=0)
    total_equity: float | None = None
    diluted_shares: float | None = Field(default=None, gt=0)
    diluted_eps: float | None = None
    sources: list[SourceMetadata] = Field(min_length=1)


class RawCurrentTrendInput(BaseModel):
    ticker: str
    currency: str
    unit_scale: UnitScale
    as_of: date
    period_label: str
    current: CurrentFinancialPeriod
    prior_comparable: CurrentFinancialPeriod
    current_ttm_ebitda: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_comparability_and_no_lookahead(self) -> "RawCurrentTrendInput":
        if self.current.period_type != self.prior_comparable.period_type:
            raise ValueError("current and prior periods must use the same period_type")
        periods = (self.current, self.prior_comparable)
        if any(period.period_end > self.as_of for period in periods):
            raise ValueError("period_end cannot be later than as_of")
        if any(
            source.filing_date > self.as_of
            for period in periods
            for source in period.sources
        ):
            raise ValueError("source filing_date cannot be later than as_of")
        return self


class CurrentTrendInput(BaseModel):
    ticker: str
    currency: str
    as_of: date
    period_label: str
    current: CurrentFinancialPeriod
    prior_comparable: CurrentFinancialPeriod
    current_ttm_ebitda: float | None = None


def normalize_current_trend_input(raw: RawCurrentTrendInput) -> CurrentTrendInput:
    multiplier = {"units": 1.0, "thousands": 1_000.0, "millions": 1_000_000.0}[
        raw.unit_scale
    ]
    amount_fields = (
        "revenue",
        "operating_income",
        "net_income_consolidated",
        "cfo",
        "capex",
        "cash",
        "total_debt",
        "total_equity",
        "diluted_shares",
    )

    def normalize_period(period: CurrentFinancialPeriod) -> CurrentFinancialPeriod:
        values = period.model_dump()
        for field in amount_fields:
            if values[field] is not None:
                values[field] *= multiplier
        return CurrentFinancialPeriod(**values)

    return CurrentTrendInput(
        ticker=raw.ticker,
        currency=raw.currency.upper(),
        as_of=raw.as_of,
        period_label=raw.period_label,
        current=normalize_period(raw.current),
        prior_comparable=normalize_period(raw.prior_comparable),
        current_ttm_ebitda=(
            raw.current_ttm_ebitda * multiplier
            if raw.current_ttm_ebitda is not None
            else None
        ),
    )


def load_current_trend_input(path: str | Path) -> CurrentTrendInput:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = RawCurrentTrendInput.model_validate(data)
    return normalize_current_trend_input(raw)
