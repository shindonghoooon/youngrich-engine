from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CaseType(str, Enum):
    PROFITABLE_GROWTH = "profitable_growth"
    LOSS_MAKING_GROWTH = "loss_making_growth"
    CYCLICAL = "cyclical"
    QUALITY_COMPOUNDER = "quality_compounder"
    LARGECAP_VALUE = "largecap_value"
    ASSET_SPECIAL = "asset_special"


class CapitalModel(str, Enum):
    ASSET_LIGHT = "asset_light"
    MANUFACTURING = "manufacturing"
    CAPITAL_INTENSIVE = "capital_intensive"
    PROJECT_BASED = "project_based"
    RD_IP_DRIVEN = "rd_ip_driven"


class Grade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    X = "X"


class Trend(str, Enum):
    ACCELERATING = "accelerating"
    STABLE = "stable"
    DECELERATING = "decelerating"
    NA = "na"


class MetricResult(BaseModel):
    name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    grade: Optional[Grade] = None
    trend: Trend = Trend.NA
    weight: float = Field(ge=0, le=1)
    supporting_tag: Optional[str] = None
    note: Optional[str] = None


class Narrative(BaseModel):
    why_growth: str
    why_continue: str
    why_this_company: str
    market_missing: str
    thesis_break: str


class Valuation(BaseModel):
    status: str = "not_evaluated"
    current_price: Optional[float] = None
    bear_value: Optional[float] = None
    base_value: Optional[float] = None
    bull_value: Optional[float] = None


class TrackingItem(BaseModel):
    name: str
    source: Optional[str] = None
    upgrade_condition: Optional[str] = None
    downgrade_condition: Optional[str] = None


class AnalysisSnapshot(BaseModel):
    ticker: str
    company_name: str
    as_of: str
    case: CaseType
    capital_model: CapitalModel

    quant_score: Optional[float] = None
    quant_grade: Optional[Grade] = None
    metrics: list[MetricResult] = []

    valuation: Valuation = Valuation()
    narrative: Optional[Narrative] = None
    risks: list[str] = []
    expectation_gap: Optional[str] = None
    tracking: list[TrackingItem] = []

    investment_grade: Optional[str] = None
