from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


UnitScale = Literal["units", "thousands", "millions"]


class SourceMetadata(BaseModel):
    type: str
    reference: str
    filing_date: date
    retrieved_at: datetime


class RawFinancialPeriod(BaseModel):
    fiscal_year: int
    fiscal_period_end: date
    revenue: float
    operating_income: float
    pretax_income: float
    income_tax_expense: float
    net_income_consolidated: float
    net_income_common: float | None = None
    cfo: float
    capex: float = Field(ge=0)
    cash: float = Field(ge=0)
    total_debt: float = Field(ge=0)
    total_equity: float
    diluted_shares: float = Field(gt=0)
    diluted_eps: float
    supplied_ebitda: float | None = None
    sources: list[SourceMetadata] = Field(min_length=1)


class RawFinancialHistory(BaseModel):
    ticker: str
    company_name: str
    currency: str
    unit_scale: UnitScale
    periods: list[RawFinancialPeriod] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_periods(self) -> "RawFinancialHistory":
        years = [period.fiscal_year for period in self.periods]
        if len(years) != len(set(years)):
            raise ValueError("fiscal_year must be unique")
        if not self.periods:
            raise ValueError("at least one financial period is required")
        return self


class FinancialPeriod(BaseModel):
    fiscal_year: int
    fiscal_period_end: date
    revenue: float
    operating_income: float
    pretax_income: float
    income_tax_expense: float
    net_income_consolidated: float
    net_income_common: float | None = None
    cfo: float
    capex: float
    cash: float
    total_debt: float
    total_equity: float
    diluted_shares: float
    diluted_eps: float
    supplied_ebitda: float | None = None
    sources: list[SourceMetadata] = Field(min_length=1)


class FinancialHistory(BaseModel):
    ticker: str
    company_name: str
    currency: str
    periods: list[FinancialPeriod]

    @model_validator(mode="after")
    def sort_and_validate_periods(self) -> "FinancialHistory":
        self.periods.sort(key=lambda period: period.fiscal_period_end)
        years = [period.fiscal_year for period in self.periods]
        if len(years) != len(set(years)):
            raise ValueError("fiscal_year must be unique")
        return self


def normalize_financial_history(raw: RawFinancialHistory) -> FinancialHistory:
    multiplier = {"units": 1.0, "thousands": 1_000.0, "millions": 1_000_000.0}[
        raw.unit_scale
    ]
    amount_fields = (
        "revenue",
        "operating_income",
        "pretax_income",
        "income_tax_expense",
        "net_income_consolidated",
        "net_income_common",
        "cfo",
        "capex",
        "cash",
        "total_debt",
        "total_equity",
        "diluted_shares",
        "supplied_ebitda",
    )
    periods: list[FinancialPeriod] = []
    for period in raw.periods:
        values = period.model_dump()
        for field in amount_fields:
            if values[field] is not None:
                values[field] *= multiplier
        periods.append(FinancialPeriod(**values))

    return FinancialHistory(
        ticker=raw.ticker,
        company_name=raw.company_name,
        currency=raw.currency.upper(),
        periods=periods,
    )


def load_financial_history(path: str | Path) -> FinancialHistory:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return normalize_financial_history(RawFinancialHistory.model_validate(data))
