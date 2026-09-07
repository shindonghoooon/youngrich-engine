"""Read-only display projection of an initial analysis, never a new evaluation.

Field aliases let the existing decision-trace renderer show both stored initial
analyses and legacy price-only evaluations without rerunning an engine.
"""
from datetime import date, datetime
from typing import Literal

from engine.tracking_models import (
    AnalysisCase, FrozenDomainModel, InvestmentGradePolicyVersion,
    InvestmentGradeSnapshot, PriceBasis, ValuationSnapshot,
)


class StoredAnalysisView(FrozenDomainModel):
    is_initial_analysis: Literal[True] = True
    evaluation_id: str
    reference_analysis_snapshot_id: str
    instrument_id: str
    ticker: str
    case: AnalysisCase
    investment_grade_result: InvestmentGradeSnapshot
    valuation_result: ValuationSnapshot | None
    investment_grade_policy_version: InvestmentGradePolicyVersion
    usage_mode: Literal["DEMO/VALIDATION", "APPROVED"]
    assumption_usage: Literal["DEMO/VALIDATION", "APPROVED"] | None
    assumption_set_id: str | None
    assumption_version: int | None
    assessment_as_of: datetime
    original_analysis_as_of: datetime
    financial_available_at: datetime
    financial_period_label: str
    financial_unit: str
    accounting_scope: str
    share_basis_version: str | None
    created_at: datetime
    unresolved_reasons: tuple[str, ...]
    price_snapshot_id: str | None
    price_session_date: date | None
    price_timestamp: datetime | None
    price_basis: PriceBasis | None
    price: float | None
    currency: str
    tracking_kpi_status: str


def stored_analysis_view(analysis, price, receipt) -> StoredAnalysisView:
    raw, result = receipt.payload["input"], receipt.payload["result"]
    v = raw["valuation"]
    return StoredAnalysisView(
        evaluation_id=analysis.snapshot_id,
        reference_analysis_snapshot_id=analysis.snapshot_id,
        instrument_id=receipt.instrument_id, ticker=analysis.ticker, case=analysis.case,
        investment_grade_result=analysis.investment_grade, valuation_result=analysis.valuation,
        investment_grade_policy_version=InvestmentGradePolicyVersion.V1_1,
        usage_mode=raw["usage"], assumption_usage=v["usage"] if v else None,
        assumption_set_id=v["assumptions"]["assumption_set_id"] if v else None,
        assumption_version=v["assumptions"]["version"] if v else None,
        assessment_as_of=analysis.as_of, original_analysis_as_of=analysis.as_of,
        financial_available_at=analysis.quant.available_at,
        financial_period_label=analysis.quant.period_end.isoformat(),
        financial_unit=f'{raw["financial_currency"]} x {raw["financial_unit_scale"]}',
        accounting_scope=raw["accounting_scope"], share_basis_version=v["share_basis_version"] if v else None,
        created_at=raw["created_at"], unresolved_reasons=tuple(result["unresolved_reasons"]),
        price_snapshot_id=price.price_snapshot_id if price else None,
        price_session_date=raw["price_session_date"], price_timestamp=price.timestamp if price else None,
        price_basis=price.price_basis if price else None, price=price.price if price else None,
        currency=raw["instrument"]["currency"], tracking_kpi_status=result["tracking_kpi_status"],
    )
