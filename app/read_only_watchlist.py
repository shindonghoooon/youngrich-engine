"""Local read-only Streamlit view for stored limited-operating evaluations."""

from __future__ import annotations

import argparse
import html
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from textwrap import dedent

import streamlit as st

from engine.limited_operating import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_DB_PATH,
    OperatingEvaluation,
)
from engine.read_only_watchlist import (
    WatchlistDataError,
    WatchlistErrorCode,
    WatchlistItem,
    WatchlistItemState,
    load_watchlist,
)
from engine.tracking_models import (
    BinaryEvidenceState,
    ResolutionState,
    TrendFlag,
)


DB_ENV = "YOUNGRICH_WATCHLIST_DB_PATH"
ARTIFACT_ENV = "YOUNGRICH_WATCHLIST_ARTIFACT_PATH"

REASON_LABELS = {
    "VALUATION_ASSUMPTIONS_UNAVAILABLE": "가치평가 가정 없음",
    "MANDATORY_NARRATIVE_UNRESOLVED": "사업 근거 부족",
    "VALUATION_COMBINATION_UNRESOLVED": "가치평가 조합의 등급 기준 미정의",
    "VALUATION_UNRESOLVED": "가치평가 자료 부족",
    "VALUATION_EVIDENCE_UNRESOLVED": "가치평가 근거 부족",
    "MANDATORY_QUANT_UNRESOLVED": "기업등급 근거 부족",
    "MANDATORY_QUANT_METRICS_MISSING": "필수 기업지표 부족",
    "SHARE_SPLIT_BASIS_UNRESOLVED": "주식수·분할 기준 미확인",
    "INVESTMENT_GRADE_UNRESOLVED": "투자등급 판단 보류",
    "CURRENT_UNRESOLVED_OPTIONAL": "최근 실적 추세 미확인",
    "Valuation Confidence cap": "가치평가 신뢰도 상한",
    "Case 2 Narrative gate cap": "사업 근거 상한",
    "Case 1 Quant cap": "기업등급 상한",
    "Case 2 Quant cap": "기업등급 상한",
    "Current Trend cap": "최근 실적 추세 상한",
    "Commercial Deterioration cap": "사업 악화 상한",
    "Funding Stress cap": "자금 부담 상한",
    "THESIS_BREAKER_OR_NARRATIVE_BROKEN": "핵심 투자 논리 훼손",
}

REASON_SENTENCES = {
    "VALUATION_ASSUMPTIONS_UNAVAILABLE": "가치평가 가정이 없습니다.",
    "MANDATORY_NARRATIVE_UNRESOLVED": "투자 판단에 필요한 사업 근거가 부족합니다.",
    "VALUATION_COMBINATION_UNRESOLVED": "현재 가치평가 결과 조합에 승인된 투자등급 규칙이 없습니다.",
    "VALUATION_UNRESOLVED": "가치평가 결과를 확정할 자료가 부족합니다.",
    "VALUATION_EVIDENCE_UNRESOLVED": "가치평가 근거를 확인할 수 없습니다.",
    "MANDATORY_QUANT_UNRESOLVED": "기업등급의 필수 근거가 부족합니다.",
    "MANDATORY_QUANT_METRICS_MISSING": "필수 기업지표가 누락되었습니다.",
    "SHARE_SPLIT_BASIS_UNRESOLVED": "주식수와 분할 기준을 확인할 수 없습니다.",
    "INVESTMENT_GRADE_UNRESOLVED": "투자등급을 확정할 조건이 부족합니다.",
}

REASON_REQUIREMENTS = {
    "VALUATION_ASSUMPTIONS_UNAVAILABLE": "가치평가 가정",
    "MANDATORY_NARRATIVE_UNRESOLVED": "사업 근거",
    "VALUATION_COMBINATION_UNRESOLVED": "가치평가 조합의 등급 기준",
    "VALUATION_UNRESOLVED": "가치평가 자료",
    "VALUATION_EVIDENCE_UNRESOLVED": "가치평가 근거",
    "MANDATORY_QUANT_UNRESOLVED": "기업등급 근거",
    "MANDATORY_QUANT_METRICS_MISSING": "필수 기업지표",
    "SHARE_SPLIT_BASIS_UNRESOLVED": "주식수·분할 기준",
}

CASE_LABELS = {
    "case1_profitable_growth": "Case 1 · 흑자 성장",
    "case2_emerging_asymmetric_growth": "Case 2 · 비대칭 성장",
}

METRIC_LABELS = {
    "revenue_growth": "매출 성장률",
    "operating_profit_growth": "영업이익 성장률",
    "margin_trend": "영업이익률 변화",
    "cash_economics": "현금 전환",
    "capital_efficiency": "자본 효율성",
    "balance_sheet": "재무 안정성",
    "dilution": "주식수 증가율",
    "per_share_growth": "주당이익 성장률",
    "gross_profit_growth": "매출총이익 성장률",
    "cash_burn_trend": "현금 소진 추세",
    "runway": "현금 여력",
    "revenue_per_share_growth": "주당 매출 성장률",
    "gross_margin_trend": "매출총이익률 변화",
    "incremental_operating_margin": "증분 영업이익률",
    "potential_dilution": "잠재 희석",
    "growth_scope": "성장 비교 범위",
}

PERCENT_METRICS = frozenset(
    {
        "revenue_growth",
        "operating_profit_growth",
        "capital_efficiency",
        "dilution",
        "per_share_growth",
        "gross_profit_growth",
        "revenue_per_share_growth",
        "incremental_operating_margin",
    }
)
MULTIPLE_METRICS = frozenset(
    {"cash_economics", "balance_sheet", "cash_burn_trend"}
)
PERCENTAGE_POINT_METRICS = frozenset({"margin_trend"})
RATIO_TO_PERCENTAGE_POINT_METRICS = frozenset({"gross_margin_trend"})
MONTH_METRICS = frozenset({"runway"})

SIGNAL_LABELS = {
    "revenue_momentum": "매출 흐름",
    "gross_profit_momentum": "매출총이익 흐름",
    "cash_burn_momentum": "현금 소진 흐름",
    "funding_runway": "자금 여력",
    "thesis_kpi_momentum": "핵심 사업지표 흐름",
}

DIRECTION_LABELS = {
    "strong_positive": "강한 개선",
    "positive": "개선",
    "mixed": "혼재",
    "neutral": "보합",
    "negative": "악화",
    "unresolved": "자료 부족",
}

FLAG_LABELS = {
    TrendFlag.FUNDING_STRESS: "자금 부담",
    TrendFlag.COMMERCIAL_INFLECTION: "상업화 전환",
    TrendFlag.COMMERCIAL_DETERIORATION: "사업 악화",
}

BINARY_STATE_LABELS = {
    BinaryEvidenceState.YES: "있음",
    BinaryEvidenceState.NO: "없음",
    BinaryEvidenceState.UNKNOWN: "미확인",
}

VALUE_LABELS = {
    "same_scope": "동일 범위",
    "pro_forma_comparable": "프로포마 비교 가능",
    "acquisition_influenced": "인수 영향 포함",
    "unresolved": "자료 부족",
    "not_applicable": "적용 대상 아님",
    "n/a": "적용 대상 아님",
    "see source fixture": "원천 자료 확인 필요",
    "burning_to_positive": "현금 소진에서 잉여현금흐름 흑자로 전환",
    "positive_to_burning": "잉여현금흐름 흑자에서 현금 소진으로 전환",
    "fcf_positive": "잉여현금흐름 흑자 유지",
}

EXPECTATION_GAP_LABELS = {
    "positive": "유리",
    "favorable": "유리",
    "overlap": "적정 범위",
    "negative": "불리",
    "unfavorable": "불리",
    "unresolved": "자료 부족",
}

CONFIDENCE_LABELS = {
    "high": "높음",
    "medium": "보통",
    "low": "낮음",
    "unresolved": "자료 부족",
}

ADJUSTMENT_TRIGGER_LABELS = {
    "quant": "기업등급",
    "narrative": "사업 근거",
    "commercial_inflection": "상업화 전환",
    "valuation_confidence": "가치평가 신뢰도",
    "case1_quant": "기업등급",
    "case2_quant": "기업등급",
    "case2_narrative": "사업 근거",
    "current_trend": "최근 실적 추세",
    "commercial_deterioration": "사업 악화",
    "funding_stress": "자금 부담",
    "thesis_breaker": "투자 논리 훼손",
}

NARRATIVE_DIMENSION_LABELS = {
    "differentiation": "차별성",
    "defensibility": "방어력",
    "adoption": "채택",
    "penetration_expansion": "침투·확장",
    "durability": "지속성",
    "failure_mode": "실패 가능성",
}

NARRATIVE_STATE_LABELS = {
    "proven": "입증",
    "strong": "강함",
    "emerging": "형성 중",
    "weak": "약함",
    "unresolved": "자료 부족",
}

CHANGE_TYPE_LABELS = {
    "PRICE_ONLY": "가격 변화",
    "FUNDAMENTAL_CHANGE": "실적·사업 변화",
    "POLICY_CHANGE": "정책 버전 변화",
    "ASSUMPTION_CHANGE": "가정 변화",
    "MIXED": "복합 변화",
    "UNRESOLVED": "비교 자료 부족",
}

ACCESSIBLE_COLOR_PAIRS = (
    ("#111827", "#FFFFFF"),
    ("#4B5563", "#FFFFFF"),
    ("#374151", "#FFFFFF"),
    ("#111827", "#E5E7EB"),
    ("#111827", "#F3F4F6"),
    ("#FFFFFF", "#111827"),
    ("#78350F", "#FFFBEB"),
    ("#1D4ED8", "#FFFFFF"),
)

APP_CSS = """
<style>
.block-container {
  max-width: 1180px;
  padding-top: 1.8rem;
  padding-left: clamp(.85rem, 4vw, 3rem);
  padding-right: clamp(.85rem, 4vw, 3rem);
}
[data-testid="stMarkdownContainer"], [data-testid="stMetric"] {
  overflow-wrap: anywhere;
}
[data-testid="stExpander"] { margin-bottom: .8rem; }
[data-testid="stDataFrame"] { margin-top: .35rem; max-width: 100%; }
.yr-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  margin: .65rem 0 1.1rem;
}
.yr-card {
  min-width: 0;
  border: 1px solid #D1D5DB;
  border-radius: 14px;
  background: #FFFFFF;
  color: #111827;
  padding: 1.05rem;
  box-shadow: 0 1px 2px rgba(17, 24, 39, .08);
  overflow-wrap: anywhere;
}
.yr-card h3 { color: #111827; font-size: 1.35rem; margin: 0 0 .2rem; }
.yr-company { color: #4B5563; min-height: 2.5rem; margin-bottom: .45rem; }
.yr-case { color: #374151; font-weight: 650; margin-bottom: .7rem; }
.yr-chips { display: flex; flex-wrap: wrap; gap: .35rem; margin: .35rem 0 .8rem; }
.yr-chip {
  background: #E5E7EB;
  color: #111827;
  border-radius: 999px;
  font-size: .78rem;
  font-weight: 650;
  padding: .2rem .5rem;
}
.yr-grade-grid {
  display: grid;
  grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr);
  gap: .55rem;
  margin: .7rem 0;
}
.yr-grade-box {
  min-width: 0;
  border-radius: 10px;
  background: #F3F4F6;
  color: #111827;
  padding: .7rem;
}
.yr-grade-box--primary { background: #111827; color: #FFFFFF; }
.yr-kicker { display: block; font-size: .78rem; font-weight: 650; opacity: .78; }
.yr-grade {
  display: block;
  font-size: 1.4rem;
  font-weight: 800;
  line-height: 1.25;
  margin-top: .2rem;
  white-space: normal;
}
.yr-reason {
  background: #FFFBEB;
  border-left: 4px solid #92400E;
  color: #78350F;
  border-radius: 7px;
  padding: .65rem .75rem;
  margin: .55rem 0;
  font-weight: 650;
  white-space: normal;
}
.yr-price { margin-top: .85rem; }
.yr-price strong { font-size: 1.15rem; }
.yr-date { color: #4B5563; font-size: .87rem; }
.yr-detail-hint { color: #1D4ED8; font-weight: 700; margin-top: .85rem; }
.yr-judgement-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .7rem;
  margin: .45rem 0 .8rem;
}
.yr-fact {
  min-width: 0;
  border: 1px solid #D1D5DB;
  border-radius: 10px;
  background: #FFFFFF;
  color: #111827;
  padding: .8rem;
  overflow-wrap: anywhere;
}
.yr-fact--primary { background: #111827; color: #FFFFFF; border-color: #111827; }
.yr-fact-label { display: block; font-size: .8rem; font-weight: 700; opacity: .78; }
.yr-fact-value {
  display: block;
  font-size: 1.18rem;
  font-weight: 800;
  line-height: 1.35;
  margin-top: .22rem;
  white-space: normal;
}
.yr-callout {
  border-radius: 9px;
  background: #FFFBEB;
  color: #78350F;
  padding: .8rem .9rem;
  margin: .45rem 0 .8rem;
}
.yr-callout p { margin: .2rem 0; }
.yr-trace { margin: .8rem 0; font-size: .9rem; }
.yr-trace-row { padding: .3rem 0; display: flex; flex-wrap: wrap; gap: .25rem .6rem; }
.yr-trace-row span { color: #4B5563; }
.yr-trace-step { border-left: 3px solid #D1D5DB; padding: .5rem .85rem; margin: .25rem 0; overflow-wrap: anywhere; }
@media (max-width: 1199px) {
  .yr-card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .yr-judgement-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 767px) {
  .block-container { padding-top: 1.05rem; }
  .yr-card-grid, .yr-judgement-grid { grid-template-columns: minmax(0, 1fr); }
  .yr-grade-grid { grid-template-columns: minmax(0, 1fr); }
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width: 100% !important;
    width: 100% !important;
    flex: 1 1 100% !important;
  }
}
</style>
"""


def configured_paths(argv: list[str] | None = None) -> tuple[Path, Path | None]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--artifacts", type=Path)
    args, _ = parser.parse_known_args(sys.argv[1:] if argv is None else argv)
    return (
        args.db or Path(os.environ.get(DB_ENV, DEFAULT_DB_PATH)),
        args.artifacts or (Path(os.environ[ARTIFACT_ENV]) if os.environ.get(ARTIFACT_ENV)
            else None if args.db or os.environ.get(DB_ENV) else DEFAULT_ARTIFACT_PATH),
    )


def _value(value: object | None, *, unresolved: str = "자료 부족") -> str:
    if value is None:
        return unresolved
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _number(value: float | None, digits: int = 2) -> str:
    return "자료 부족" if value is None else f"{value:,.{digits}f}"


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _case_label(value: object) -> str:
    raw = _value(value)
    return CASE_LABELS.get(raw, raw)


def _metric_label(name: str) -> str:
    return METRIC_LABELS.get(name, name.replace("_", " "))


def _direction_label(value: object) -> str:
    raw = _value(value)
    return DIRECTION_LABELS.get(raw, raw)


def _resolution_label(value: object) -> str:
    raw = _value(value)
    return "계산 완료" if raw == "resolved" else "자료 부족"


def _metric_value(metric) -> str:
    """Format a metric by semantic identity without changing its stored value."""
    value = metric.value
    if value is None:
        return "자료 부족"
    if isinstance(value, str):
        return VALUE_LABELS.get(value.lower(), VALUE_LABELS.get(value, value))
    if metric.name in MONTH_METRICS:
        return f"{value:,.1f}개월"
    if metric.name in MULTIPLE_METRICS:
        return f"{value:,.2f}배"
    if metric.name in PERCENTAGE_POINT_METRICS:
        return f"{value:+,.2f}%p"
    if metric.name in RATIO_TO_PERCENTAGE_POINT_METRICS:
        return f"{value * 100:+,.2f}%p"
    if metric.name in PERCENT_METRICS:
        return f"{value:+,.1%}"
    if metric.unit == "currency":
        return f"{value:,.2f}"
    return f"{value:,}"


def _metric_status(metric) -> str:
    raw_value = metric.value.lower() if isinstance(metric.value, str) else None
    if raw_value in {"not_applicable", "n/a", "not applicable"}:
        return "적용 대상 아님"
    if metric.state == ResolutionState.UNRESOLVED:
        return "자료 부족"
    if not metric.is_core and metric.grade is None:
        return "참고 지표 · 등급 미부여"
    if metric.is_core and metric.grade is None:
        return "원문 확인 필요"
    return "평가 완료"


def _metric_rows(
    metrics,
    *,
    period_label: str,
    include_grade: bool,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for metric in metrics:
        row = {
            "지표": _metric_label(metric.name),
            "값": _metric_value(metric),
            "상태": _metric_status(metric),
            "평가기간": period_label,
        }
        if include_grade:
            row["등급"] = _value(metric.grade, unresolved="—")
        rows.append(row)
    return rows


def _metric_notes(metrics) -> list[tuple[str, str]]:
    return [
        (_metric_label(metric.name), metric.note)
        for metric in metrics
        if metric.note
    ]


def _expectation_gap(evaluation: OperatingEvaluation) -> str:
    if evaluation.valuation_result is None:
        return "자료 부족"
    raw = evaluation.valuation_result.output.expectation_gap.value
    return EXPECTATION_GAP_LABELS.get(raw, raw)


def _investment_grade(value, *, show_code: bool = False) -> str:
    if value.value == "U":
        return "판단 보류 (코드 U)" if show_code else "판단 보류"
    return value.value


def _reason_label(reason: str) -> str:
    if reason in REASON_LABELS:
        return REASON_LABELS[reason]
    if reason.startswith("MANDATORY_QUANT_METRICS_MISSING"):
        return "필수 기업지표 부족"
    return "기타 미해결 사유"


def _reason_sentence(reason: str) -> str:
    if reason in REASON_SENTENCES:
        return REASON_SENTENCES[reason]
    if reason.startswith("MANDATORY_QUANT_METRICS_MISSING"):
        return "필수 기업지표가 누락되었습니다."
    return "저장된 사유 코드를 확인해야 합니다."


def _reason_requirement(reason: str) -> str | None:
    if reason.startswith("MANDATORY_QUANT_METRICS_MISSING"):
        return "필수 기업지표"
    return REASON_REQUIREMENTS.get(reason)


def _reason_detail(reason: str) -> str | None:
    if reason == "VALUATION_COMBINATION_UNRESOLVED":
        return "저장된 세부 원인 정보 없음"
    return None


def _primary_reason(reasons: tuple[str, ...]) -> str | None:
    priority = (
        "VALUATION_ASSUMPTIONS_UNAVAILABLE",
        "VALUATION_COMBINATION_UNRESOLVED",
        "VALUATION_EVIDENCE_UNRESOLVED",
        "MANDATORY_NARRATIVE_UNRESOLVED",
        "MANDATORY_QUANT_UNRESOLVED",
    )
    for candidate in priority:
        if candidate in reasons:
            return candidate
    return reasons[0] if reasons else None


def _status_labels(item: WatchlistItem) -> tuple[str, ...]:
    evaluation = item.evaluation
    price = item.price_snapshot
    if evaluation is None:
        return ()
    labels: list[str] = []
    if price is not None and price.source == "SYNTHETIC_TEST_ONLY":
        labels.append("예시 데이터")
    if _value(evaluation.usage_mode) == "DEMO/VALIDATION":
        labels.append("검증 데이터")
    if evaluation.assumption_set_id is not None and _value(getattr(evaluation, "assumption_usage", evaluation.usage_mode)) == "DEMO/VALIDATION":
        labels.append("검증용 가정")
    return tuple(labels)


def _assumption_label(evaluation: OperatingEvaluation) -> str:
    if evaluation.assumption_set_id is None:
        return "없음"
    return f"{evaluation.assumption_set_id} / v{evaluation.assumption_version}"


def _price_label(evaluation) -> str:
    return f"{evaluation.price:,.2f} {evaluation.currency}" if evaluation.price is not None else "저장된 가격 평가 없음"


def _price_date_label(evaluation) -> str:
    return f"{evaluation.price_session_date.isoformat()} 종가" if evaluation.price_session_date else "가격 기준일 없음"


def _active_adjustments(evaluation: OperatingEvaluation) -> list[str]:
    adjustments: list[str] = []
    for item in evaluation.investment_grade_result.adjustments:
        if not item.active:
            continue
        trigger = ADJUSTMENT_TRIGGER_LABELS.get(
            item.trigger.value, item.trigger.value
        )
        if item.adjustment_type.value == "gate":
            adjustments.append(_reason_label(item.reason))
        elif item.maximum_grade is not None:
            adjustments.append(
                f"{trigger}에 따른 등급 상한 "
                f"{_investment_grade(item.maximum_grade)}"
            )
        else:
            adjustments.append(f"{trigger}: {_reason_label(item.reason)}")
    return adjustments


@dataclass(frozen=True)
class DecisionTraceStep:
    """Display-only projection; never applies a grade or cap."""

    label: str
    display_value: str
    impact: str
    explanation: str
    source_code: tuple[str, ...] = ()


def _decision_trace(item: WatchlistItem) -> tuple[DecisionTraceStep, ...]:
    evaluation, analysis = item.evaluation, item.reference_analysis
    assert evaluation is not None and analysis is not None
    result = evaluation.investment_grade_result
    valuation = evaluation.valuation_result
    current = analysis.current_trend
    steps = [
        DecisionTraceStep(
            "가치평가 초기 판단",
            _investment_grade(result.initial_valuation_grade),
            "UNRESOLVED" if result.initial_valuation_grade.value == "U" else "NOT_RECORDED",
            "가치평가 계산 완료" if valuation is not None
            and valuation.state == ResolutionState.RESOLVED else "가치평가 미산출",
            (result.rationale,) if result.rationale else (),
        )
    ]

    def axis(label, value, trigger, unresolved=False):
        recorded = tuple(a for a in result.adjustments if a.trigger.value == trigger)
        active = tuple(a for a in recorded if a.active)
        impact = "UNRESOLVED" if unresolved else "NOT_RECORDED"
        explanation = "추가 판정 제한 기록 없음"
        if recorded and not active:
            impact, explanation = "NO_CHANGE", "비활성 판정 제한 기록"
        if active:
            impact = "BLOCK" if any(a.adjustment_type.value == "gate" for a in active) else "CAP"
            explanation = " · ".join(
                _reason_label(a.reason) if a.adjustment_type.value == "gate"
                else "등급 상한 " + _investment_grade(a.maximum_grade)
                for a in active
            )
        steps.append(DecisionTraceStep(
            label, value, impact, explanation, tuple(a.reason for a in recorded)
        ))

    quant = analysis.quant
    axis(
        "기업 분석",
        ("완료 · 기업등급 " + _value(quant.grade))
        if quant.state == ResolutionState.RESOLVED else "기업 분석 필수 근거 부족",
        "quant", quant.state != ResolutionState.RESOLVED,
    )
    gate_labels = {
        "confirmed": "확인됨", "qualified": "조건부 확인", "developing": "형성 중",
        "weak": "약함", "broken": "훼손", "unresolved": "미확인",
    }
    gate = analysis.narrative_gate
    narrative = analysis.narrative
    narrative_value = (
        "사업 근거 판정: " + gate_labels.get(gate.value, gate.value)
        if gate is not None else "사업 근거 판정 기록 없음"
    )
    if narrative is not None:
        narrative_value += " · 평가 " + NARRATIVE_STATE_LABELS.get(
            narrative.overall.value, narrative.overall.value
        )
    axis("사업 근거", narrative_value, "narrative", gate is None or gate.value == "unresolved")
    axis("최근 실적 추세", _direction_label(current.overall) if current else "미확인",
         "current_trend", current is None or current.overall.value == "unresolved")
    flags = {r.flag: r.state for r in current.flag_results} if current else {}
    funding = flags.get(TrendFlag.FUNDING_STRESS, BinaryEvidenceState.UNKNOWN)
    axis("자금 부담", BINARY_STATE_LABELS[funding], "funding_stress",
         funding == BinaryEvidenceState.UNKNOWN)
    confidence = valuation.output.confidence.value if valuation else "unresolved"
    axis("가치평가 신뢰도", CONFIDENCE_LABELS[confidence], "valuation_confidence",
         confidence == "unresolved")
    axis("투자 논리 훼손", "있음" if result.thesis_breaker_active else "트리거 비활성",
         "thesis_breaker")
    steps.append(DecisionTraceStep(
        "최종 투자등급", _investment_grade(result.final_grade),
        "BLOCK" if result.final_grade.value == "U" else "NOT_RECORDED",
        " · ".join(_reason_label(r) for r in evaluation.unresolved_reasons)
        or "저장된 최종 판단",
        evaluation.unresolved_reasons,
    ))
    return tuple(steps)


def _trace_summary_html(item: WatchlistItem) -> str:
    steps = _decision_trace(item)
    evaluation = item.evaluation
    assert evaluation is not None
    if evaluation.valuation_result is None:
        rows = [
            ("기업 분석", steps[1].display_value),
            ("가격", "평가 가격 확인됨" if item.price_snapshot else "가격 기록 없음"),
            ("가치평가 초기 판단", steps[0].display_value + " · " + steps[0].explanation),
        ]
    else:
        rows = [
            ("가치평가 초기 판단", steps[0].display_value + " · " + steps[0].explanation),
            ("기업 분석", steps[1].display_value),
            ("최근 실적 추세", steps[3].display_value),
        ]
    rows.append(("최종 투자등급", steps[-1].display_value))
    return '<div class="yr-trace"><strong>판단 근거</strong>' + "".join(
        '<div class="yr-trace-row"><span>' + _escape(label)
        + '</span><strong>' + _escape(value) + '</strong></div>'
        for label, value in rows
    ) + "</div>"


def _render_decision_trace(item: WatchlistItem) -> None:
    evaluation = item.evaluation
    assert evaluation is not None
    result = evaluation.investment_grade_result
    st.subheader("투자등급 결정 경로")
    for step in _decision_trace(item):
        st.markdown(
            '<div class="yr-trace-step"><strong>' + _escape(step.label)
            + '</strong><div>' + _escape(step.display_value) + '</div><small>'
            + _escape(step.explanation) + '</small></div>',
            unsafe_allow_html=True,
        )
    st.write("저장된 판정 제한 적용 순서")
    st.write("가치평가 초기 판단: " + _investment_grade(result.initial_valuation_grade))
    active = [a for a in result.adjustments if a.active]
    for adjustment in active:
        trigger = ADJUSTMENT_TRIGGER_LABELS.get(adjustment.trigger.value, adjustment.trigger.value)
        restriction = (
            "판단 보류" if adjustment.maximum_grade is not None
            and adjustment.maximum_grade.value == "U"
            else "등급 상한 " + _investment_grade(adjustment.maximum_grade)
            if adjustment.maximum_grade is not None else "판정 제한"
        )
        st.write(
            f"↓ {adjustment.sequence}. {trigger} · {restriction} · "
            + _reason_label(adjustment.reason)
        )
    if not active:
        st.caption("활성 판정 제한 기록 없음")
    st.write("최종 투자등급: " + _investment_grade(result.final_grade))
    if result.initial_valuation_grade == result.final_grade:
        st.caption("초기 판단과 최종 판단이 같습니다. 기록된 상한도 함께 표시합니다.")
    elif not active:
        st.caption("초기·최종 등급이 다르지만 변경 사유의 판정 제한 기록은 없습니다.")
    st.caption("각 제한 적용 후 중간 등급은 저장되어 있지 않아 별도로 계산하지 않습니다.")
    with st.expander("판정 근거 자세히"):
        for step in _decision_trace(item):
            st.write(f"{step.label}: {step.impact}")
            for code in step.source_code:
                st.code(code, language=None)
        st.write(f"가정: {_assumption_label(evaluation)}")
        st.write(f"정책: {evaluation.investment_grade_policy_version.value}")
        st.write(f"모델: {result.model_version}")
        st.json(result.model_dump(mode="json"), expanded=False)


def _summary_card_html(item: WatchlistItem) -> str:
    if item.state != WatchlistItemState.READY:
        message = _escape(item.message or "저장된 데이터 없음")
        return (
            '<article class="yr-card">'
            f"<h3>{_escape(item.ticker)}</h3>"
            f'<div class="yr-reason">{message}</div>'
            '<div class="yr-detail-hint">상세 분석할 저장 결과가 없습니다.</div>'
            "</article>"
        )

    evaluation = item.evaluation
    analysis = item.reference_analysis
    assert evaluation is not None and analysis is not None
    labels = "".join(
        f'<span class="yr-chip">{_escape(label)}</span>'
        for label in _status_labels(item)
    )
    grade = _investment_grade(evaluation.investment_grade_result.final_grade)
    reason = ""
    primary_reason = _primary_reason(evaluation.unresolved_reasons)
    if primary_reason is not None:
        reason = (
            '<div class="yr-reason">'
            + _escape(_reason_label(primary_reason))
            + "</div>"
        )
    else:
        adjustments = _active_adjustments(evaluation)
        if adjustments:
            reason = (
                '<div class="yr-reason">주요 판정 제한: '
                + _escape(adjustments[0])
                + "</div>"
            )

    return dedent(
        f"""
        <article class="yr-card">
      <h3>{_escape(item.ticker)}</h3>
      <div class="yr-company">{_escape(analysis.company_name)}</div>
      <div class="yr-case">{_escape(_case_label(analysis.case))}</div>
      <div class="yr-chips">{labels}</div>
      <div class="yr-grade-grid">
        <div class="yr-grade-box">
          <span class="yr-kicker">기업등급</span>
          <span class="yr-grade">{_escape(_value(analysis.quant.grade))}</span>
        </div>
        <div class="yr-grade-box yr-grade-box--primary">
          <span class="yr-kicker">투자등급</span>
          <span class="yr-grade">{_escape(grade)}</span>
        </div>
      </div>
      {_trace_summary_html(item)}
      {reason}
      <div class="yr-price">
        <span class="yr-kicker">평가에 사용한 가격</span>
        <strong>{_escape(_price_label(evaluation))}</strong>
        <div class="yr-date">{_escape(_price_date_label(evaluation))}</div>
      </div>
      <div class="yr-detail-hint">아래에서 상세 분석 보기 ↓</div>
        </article>
        """
    ).strip()


def _render_summary(snapshot) -> None:
    cards = "".join(_summary_card_html(item) for item in snapshot.items)
    st.markdown(
        f'<section class="yr-card-grid" aria-label="관심종목 요약">{cards}</section>',
        unsafe_allow_html=True,
    )


def _render_reason_summary(evaluation: OperatingEvaluation) -> None:
    if not evaluation.unresolved_reasons:
        return
    primary = _primary_reason(evaluation.unresolved_reasons)
    ordered_reasons = (
        (primary,)
        + tuple(
            reason
            for reason in evaluation.unresolved_reasons
            if reason != primary
        )
        if primary is not None
        else evaluation.unresolved_reasons
    )
    for reason in ordered_reasons:
        requirement = _reason_requirement(reason)
        detail = _reason_detail(reason)
        lines = [
            f"<p><strong>사유</strong><br>{_escape(_reason_sentence(reason))}</p>"
        ]
        if requirement:
            lines.append(
                f"<p><strong>확인 필요</strong><br>{_escape(requirement)}</p>"
            )
        if detail:
            lines.append(
                f"<p><strong>상세 원인</strong><br>{_escape(detail)}</p>"
            )
        st.markdown(
            '<div class="yr-callout">' + "".join(lines) + "</div>",
            unsafe_allow_html=True,
        )


def _render_judgement(item: WatchlistItem) -> None:
    evaluation = item.evaluation
    analysis = item.reference_analysis
    assert evaluation is not None and analysis is not None

    st.subheader("판단 요약")
    st.markdown(
        f"""
        <section class="yr-judgement-grid" aria-label="판단 요약">
          <div class="yr-fact">
            <span class="yr-fact-label">기업등급</span>
            <span class="yr-fact-value">{_escape(_value(analysis.quant.grade))}</span>
          </div>
          <div class="yr-fact yr-fact--primary">
            <span class="yr-fact-label">투자등급</span>
            <span class="yr-fact-value">{_escape(_investment_grade(evaluation.investment_grade_result.final_grade))}</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    _render_decision_trace(item)
    _render_reason_summary(evaluation)
    st.markdown(
        f"""
        <section class="yr-judgement-grid" aria-label="평가 가격과 기준일">
          <div class="yr-fact">
            <span class="yr-fact-label">평가에 사용한 가격</span>
            <span class="yr-fact-value">{_escape(_price_label(evaluation))}</span>
            <span class="yr-date">{_escape(_price_date_label(evaluation))}</span>
          </div>
          <div class="yr-fact">
            <span class="yr-fact-label">재무 기준기간</span>
            <span class="yr-fact-value">{_escape(evaluation.financial_period_label)}</span>
            <span class="yr-date">분석 기준일 {analysis.as_of.date().isoformat()}</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if not evaluation.unresolved_reasons:
        adjustments = _active_adjustments(evaluation)
        if adjustments:
            st.write("주요 판정 제한 조건")
            for adjustment in adjustments:
                st.write(f"- {adjustment}")
        else:
            st.caption("활성 판정 제한 조건 없음")
    st.caption(
        "저장된 최초 분석입니다. 가격만 갱신한 파생 평가가 아닙니다."
        if getattr(evaluation, "is_initial_analysis", False) else
        "저장된 원본 분석과 가정은 그대로 두고, 지정 가격으로 만든 별도 파생 평가입니다."
    )


def _render_core_metrics(item: WatchlistItem) -> None:
    analysis = item.reference_analysis
    evaluation = item.evaluation
    assert analysis is not None and evaluation is not None
    core_metrics = [metric for metric in analysis.quant.metrics if metric.is_core]
    period_label = f"종료 {analysis.quant.period_end.isoformat()}"

    st.subheader("핵심 평가 지표")
    grade_column, score_column, status_column = st.columns(3)
    grade_column.metric("기업등급", _value(analysis.quant.grade))
    score_column.metric("기업점수", _number(analysis.quant.score))
    status_column.metric("계산 상태", _resolution_label(analysis.quant.state))
    st.caption(
        f"연간·장기 평가 기준기간: {period_label} · "
        f"재무 표기 {evaluation.financial_period_label}"
    )
    st.dataframe(
        _metric_rows(
            core_metrics,
            period_label=period_label,
            include_grade=True,
        ),
        hide_index=True,
        width="stretch",
        column_order=("지표", "값", "등급", "상태", "평가기간"),
    )


def _render_current_trend(item: WatchlistItem) -> None:
    analysis = item.reference_analysis
    assert analysis is not None
    current = analysis.current_trend

    st.subheader("최근 실적 추세")
    st.caption("최근 실적 추세는 기업등급과 별도의 최근 변화 지표입니다.")
    if current is None:
        st.info("저장된 최근 비교 자료가 없어 추세를 확인할 수 없습니다.")
        st.write("비교기간 정보 없음")
        st.caption("자금 부담 · 상업화 전환 · 사업 악화 상태: 미확인")
        return

    st.markdown(f"**종합 추세: {_direction_label(current.overall)}**")
    st.caption(f"최근 기준기간 종료일 {current.period_end.isoformat()}")
    st.caption("비교기간 정보 없음")
    st.dataframe(
        [
            {
                "항목": SIGNAL_LABELS.get(signal.name, signal.name.replace("_", " ")),
                "추세": _direction_label(signal.state),
            }
            for signal in current.signals
        ],
        hide_index=True,
        width="stretch",
    )
    flag_states = {result.flag: result.state for result in current.flag_results}
    st.caption("확인 상태")
    st.dataframe(
        [
            {
                "항목": FLAG_LABELS[flag],
                "상태": BINARY_STATE_LABELS[
                    flag_states.get(flag, BinaryEvidenceState.UNKNOWN)
                ],
            }
            for flag in TrendFlag
        ],
        hide_index=True,
        width="stretch",
    )


def _render_narrative(analysis) -> None:
    narrative = analysis.narrative
    if narrative is None:
        st.info("사업 근거: 저장된 평가 자료가 없습니다.")
        return
    st.write("사업 근거")
    overall = _value(narrative.overall)
    st.write(f"종합 상태: **{NARRATIVE_STATE_LABELS.get(overall, overall)}**")
    st.dataframe(
        [
            {
                "항목": NARRATIVE_DIMENSION_LABELS.get(
                    assessment.dimension,
                    assessment.dimension.replace("_", " "),
                ),
                "상태": NARRATIVE_STATE_LABELS.get(
                    _value(assessment.state), _value(assessment.state)
                ),
            }
            for assessment in narrative.assessments
        ],
        hide_index=True,
        width="stretch",
    )


def _render_supporting_metrics(item: WatchlistItem) -> None:
    analysis = item.reference_analysis
    assert analysis is not None
    supporting_metrics = [
        metric for metric in analysis.quant.metrics if not metric.is_core
    ]
    st.subheader("참고 지표")
    if not supporting_metrics:
        st.info("이 분석에는 별도 참고 지표가 없습니다.")
        return
    period_label = f"종료 {analysis.quant.period_end.isoformat()}"
    st.dataframe(
        _metric_rows(
            supporting_metrics,
            period_label=period_label,
            include_grade=False,
        ),
        hide_index=True,
        width="stretch",
        column_order=("지표", "값", "상태", "평가기간"),
    )


def _render_valuation_and_limits(item: WatchlistItem) -> None:
    evaluation = item.evaluation
    analysis = item.reference_analysis
    assert evaluation is not None and analysis is not None

    st.subheader("가치평가 및 판정 제한")
    st.write(
        f"평가에 사용한 가격: **{_price_label(evaluation)}** · "
        f"{_price_date_label(evaluation)}"
    )
    st.write(f"가정 상태: **{_assumption_label(evaluation)}**")
    valuation = evaluation.valuation_result
    if valuation is None:
        st.info("가치평가 상태: 자료 부족")
    else:
        output = valuation.output
        st.write(f"요구 성장률: **{_number(output.required_growth, 4)}**")
        st.write(f"기대 격차: **{_expectation_gap(evaluation)}**")
        st.write(
            "보수 / 기준 / 낙관 가치: "
            f"{_number(output.bear_value)} / "
            f"{_number(output.base_value)} / "
            f"{_number(output.bull_value)}"
        )
        st.write(
            "가치평가 신뢰도: "
            f"**{CONFIDENCE_LABELS.get(output.confidence.value, output.confidence.value)}**"
        )

    adjustments = _active_adjustments(evaluation)
    if adjustments:
        st.write("판정 제한 조건 / 등급 상한")
        for adjustment in adjustments:
            st.write(f"- {adjustment}")
    else:
        st.caption("활성 판정 제한 조건 없음")
    if evaluation.unresolved_reasons:
        st.write(
            "주요 판단 보류 사유: "
            + " · ".join(_reason_label(reason) for reason in evaluation.unresolved_reasons)
        )
    _render_narrative(analysis)


def _render_diagnostics(item: WatchlistItem) -> None:
    evaluation = item.evaluation
    analysis = item.reference_analysis
    assert evaluation is not None and analysis is not None
    with st.expander("모델·원본 정보", expanded=False):
        st.write(f"Analysis ID: `{analysis.snapshot_id}`")
        st.write(f"Evaluation ID: `{evaluation.evaluation_id}`")
        st.write(f"재무 기간: `{evaluation.financial_period_label}`")
        st.write(f"재무 공개 시각: `{evaluation.financial_available_at.isoformat()}`")
        st.write(f"원본 분석 as_of: `{evaluation.original_analysis_as_of.isoformat()}`")
        evaluation_label = "최초 분석" if getattr(evaluation, "is_initial_analysis", False) else "파생 평가"
        st.write(f"{evaluation_label} as_of: `{evaluation.assessment_as_of.isoformat()}`")
        st.write(
            f"정책: `{evaluation.investment_grade_policy_version.value}` / "
            f"`{evaluation.investment_grade_result.model_version}`"
        )
        st.write(
            f"{'최초' if getattr(evaluation, 'is_initial_analysis', False) else '파생'} 투자등급 기술 코드: "
            f"`{evaluation.investment_grade_result.final_grade.value}`"
        )
        source_grade = (
            _investment_grade(analysis.investment_grade.final_grade, show_code=True)
            if analysis.investment_grade is not None
            else "미제공"
        )
        st.write(f"원본 AnalysisSnapshot 투자등급: **{source_grade}**")
        st.write(f"Case 원문: `{analysis.case.value}`")
        st.write(f"Case 정의 버전: `{analysis.case_definition_version}`")
        st.write(f"Quant model: `{analysis.quant.model_version}`")
        st.write(f"Quant 공개 시각: `{analysis.quant.available_at.isoformat()}`")
        st.write(f"Quant as_of: `{analysis.quant.as_of.isoformat()}`")
        st.write(f"가격 timestamp: `{evaluation.price_timestamp.isoformat() if evaluation.price_timestamp else '없음'}`")
        st.write(f"원본 가격 기준: `{_value(evaluation.price_basis)}`")
        if hasattr(evaluation, "tracking_kpi_status"):
            st.write(f"추적 KPI 등록: `{evaluation.tracking_kpi_status}`")
        st.write(f"재무 단위: `{_value(evaluation.financial_unit)}`")
        st.write(f"회계 범위: `{_value(evaluation.accounting_scope)}`")
        st.write(f"주식수 기준: `{_value(evaluation.share_basis_version)}`")
        st.write(f"평가 생성 시각: `{evaluation.created_at.isoformat()}`")
        st.write("원시 판단 보류 reason code")
        if evaluation.unresolved_reasons:
            for reason in evaluation.unresolved_reasons:
                st.write(f"- {_reason_label(reason)} · `{reason}`")
        else:
            st.caption("없음")
        st.write("전체 판정 조정 기록")
        if evaluation.investment_grade_result.adjustments:
            st.json(
                [
                    adjustment.model_dump(mode="json")
                    for adjustment in evaluation.investment_grade_result.adjustments
                ],
                expanded=False,
            )
        else:
            st.caption("없음")
        st.write("지표 원본 값")
        st.dataframe(
            [
                {
                    "name": metric.name,
                    "raw_value": repr(metric.value),
                    "unit": metric.unit or "",
                    "grade": _value(metric.grade, unresolved=""),
                    "state": metric.state.value,
                    "role": "Core" if metric.is_core else "Supporting",
                }
                for metric in analysis.quant.metrics
            ],
            hide_index=True,
            width="stretch",
        )
        notes = _metric_notes(analysis.quant.metrics)
        if notes:
            st.write("지표 원문 참고")
            for label, note in notes:
                st.caption(f"{label}: {note}")
        if analysis.current_trend is not None:
            st.write("최근 실적 추세 원문 근거")
            for signal in analysis.current_trend.signals:
                label = SIGNAL_LABELS.get(signal.name, signal.name.replace("_", " "))
                st.caption(f"{label}: {signal.observation or '근거 표시 자료 없음'}")
        if analysis.thesis_status is not None:
            st.write("투자 논리·핵심 지표 원본")
            st.json(analysis.thesis_status.model_dump(mode="json"), expanded=False)


def _render_comparison(item: WatchlistItem) -> None:
    st.write("이전 평가와 비교")
    diff = item.latest_diff
    if diff is None:
        st.info("저장된 이전 평가가 없어 비교할 수 없습니다.")
        return
    change_type = _value(diff.change_type)
    st.write(
        f"변화 유형: **{CHANGE_TYPE_LABELS.get(change_type, change_type)}**"
    )
    st.write(
        f"평가 가격: {_number(diff.previous_price)} → {_number(diff.current_price)} "
        f"({diff.price_return:+.2%})"
    )
    st.write(
        "투자등급: "
        f"{_investment_grade(diff.previous_grade, show_code=True)} → "
        f"{_investment_grade(diff.current_grade, show_code=True)}"
    )
    st.write(
        "기대 격차: "
        f"{EXPECTATION_GAP_LABELS.get(_value(diff.previous_expectation_gap), _value(diff.previous_expectation_gap))}"
        " → "
        f"{EXPECTATION_GAP_LABELS.get(_value(diff.current_expectation_gap), _value(diff.current_expectation_gap))}"
    )
    if diff.unresolved_reasons:
        st.warning(
            "현재 판단 보류 사유: "
            + " · ".join(_reason_label(reason) for reason in diff.unresolved_reasons)
        )


def _render_load_error(error: WatchlistDataError) -> None:
    if error.code in {
        WatchlistErrorCode.MISSING_DATABASE,
        WatchlistErrorCode.MISSING_EVALUATIONS,
    }:
        st.info("저장된 데이터 없음")
    else:
        st.error("저장 데이터 오류")
    st.write(error.public_message)
    st.caption(
        "등록·마이그레이션은 research.watchlist, 분석은 research.stock_onboarding CLI에서 수행합니다. "
        "docs/specs/generic-stock-onboarding-v1.md 및 기존 docs/limited-operating-flow.md를 확인하세요."
    )


def main() -> None:
    st.set_page_config(
        page_title="Youngrich 저장 분석 조회",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.title("관심종목 분석")
    st.caption("저장된 분석 결과 · 읽기 전용")

    reload_requested = st.button("저장본 다시 불러오기", type="secondary")
    db_path, artifact_path = configured_paths()
    try:
        if reload_requested:
            with st.spinner("저장본을 불러오는 중입니다."):
                snapshot = load_watchlist(db_path, artifact_path)
        else:
            snapshot = load_watchlist(db_path, artifact_path)
    except WatchlistDataError as error:
        _render_load_error(error)
        return
    if reload_requested:
        st.success("저장본을 다시 불러왔습니다.")

    page_labels = sorted(
        {
            label
            for item in snapshot.items
            for label in _status_labels(item)
        }
    )
    if page_labels:
        st.caption("데이터 상태: " + " · ".join(page_labels))
        st.caption(
            "검증 데이터는 제한 운영 확인용 저장 결과이며, "
            "검증용 가정은 아직 승인 전인 가치평가 입력입니다."
        )
    st.caption(
        "투자등급: 이 평가에 사용한 가격에서의 투자 매력 · "
        "기업등급: 성장·수익·재무 상태"
    )

    st.subheader("종목 요약")
    _render_summary(snapshot)

    ready_items = {
        (item.ticker if sum(other.ticker == item.ticker for other in snapshot.items) == 1
         else f"{item.ticker} · {item.exchange} · {item.instrument_id}"): item
        for item in snapshot.items if item.state == WatchlistItemState.READY
    }
    if not ready_items:
        st.info("상세히 볼 수 있는 저장 평가가 없습니다.")
        return

    selected = st.selectbox(
        "상세 분석할 종목",
        list(ready_items),
        key="watchlist_selected_ticker",
    )
    item = ready_items[selected]
    st.divider()
    st.header(f"{selected} 상세 분석")
    _render_judgement(item)
    _render_core_metrics(item)
    _render_current_trend(item)
    _render_valuation_and_limits(item)
    _render_comparison(item)
    _render_supporting_metrics(item)
    _render_diagnostics(item)



if __name__ == "__main__":
    main()
