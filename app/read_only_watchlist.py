"""Local read-only Streamlit view for stored limited-operating evaluations."""

from __future__ import annotations

import argparse
import os
import sys
from enum import Enum
from pathlib import Path

import streamlit as st

from engine.limited_operating import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_DB_PATH,
    SUPPORTED_TICKERS,
    OperatingEvaluation,
)
from engine.read_only_watchlist import (
    WatchlistDataError,
    WatchlistErrorCode,
    WatchlistItem,
    WatchlistItemState,
    load_watchlist,
)
from engine.tracking_models import BinaryEvidenceState, TrendFlag


DB_ENV = "YOUNGRICH_WATCHLIST_DB_PATH"
ARTIFACT_ENV = "YOUNGRICH_WATCHLIST_ARTIFACT_PATH"

REASON_LABELS = {
    "VALUATION_ASSUMPTIONS_UNAVAILABLE": "가치평가 가정 없음",
    "MANDATORY_NARRATIVE_UNRESOLVED": "사업 근거 부족",
    "VALUATION_COMBINATION_UNRESOLVED": "평가 조건 판단 보류",
    "VALUATION_UNRESOLVED": "가치평가 미해결",
    "VALUATION_EVIDENCE_UNRESOLVED": "가치평가 근거 부족",
    "MANDATORY_QUANT_UNRESOLVED": "기업등급 근거 부족",
    "MANDATORY_QUANT_METRICS_MISSING": "필수 기업지표 부족",
    "SHARE_SPLIT_BASIS_UNRESOLVED": "주식수·분할 기준 미확인",
    "INVESTMENT_GRADE_UNRESOLVED": "투자등급 판단 보류",
    "CURRENT_UNRESOLVED_OPTIONAL": "최신 흐름 미확인",
    "Valuation Confidence cap": "가치평가 신뢰도 상한",
    "Case 2 Narrative gate cap": "사업 근거 상한",
    "Case 1 Quant cap": "기업등급 상한",
    "Case 2 Quant cap": "기업등급 상한",
    "Current Trend cap": "최신 흐름 상한",
    "Commercial Deterioration cap": "사업 악화 상한",
    "Funding Stress cap": "자금 부담 상한",
    "THESIS_BREAKER_OR_NARRATIVE_BROKEN": "핵심 투자 논리 훼손",
}


def configured_paths(argv: list[str] | None = None) -> tuple[Path, Path]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--artifacts", type=Path)
    args, _ = parser.parse_known_args(sys.argv[1:] if argv is None else argv)
    return (
        args.db or Path(os.environ.get(DB_ENV, DEFAULT_DB_PATH)),
        args.artifacts
        or Path(os.environ.get(ARTIFACT_ENV, DEFAULT_ARTIFACT_PATH)),
    )


def _value(value: object | None, *, unresolved: str = "미해결") -> str:
    if value is None:
        return unresolved
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _number(value: float | None, digits: int = 2) -> str:
    return "미해결" if value is None else f"{value:,.{digits}f}"


def _expectation_gap(evaluation: OperatingEvaluation) -> str:
    if evaluation.valuation_result is None:
        return "미해결"
    return evaluation.valuation_result.output.expectation_gap.value


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


def _status_labels(item: WatchlistItem) -> tuple[str, ...]:
    evaluation = item.evaluation
    price = item.price_snapshot
    if evaluation is None or price is None:
        return ()
    labels: list[str] = []
    if price.source == "SYNTHETIC_TEST_ONLY":
        labels.append("예시 데이터")
    if evaluation.assumption_set_id is not None:
        labels.append("검증용 가정")
    elif evaluation.usage_mode.value == "DEMO/VALIDATION" and not labels:
        labels.append("검증 데이터")
    return tuple(labels)


def _assumption_label(evaluation: OperatingEvaluation) -> str:
    if evaluation.assumption_set_id is None:
        return "미제공 / 미해결"
    return f"{evaluation.assumption_set_id} / v{evaluation.assumption_version}"


def _active_adjustments(evaluation: OperatingEvaluation) -> list[str]:
    return [
        (
            f"{item.trigger.value}: {_reason_label(item.reason)}"
            + (
                f" (상한 {_investment_grade(item.maximum_grade)})"
                if item.maximum_grade is not None
                else ""
            )
        )
        for item in evaluation.investment_grade_result.adjustments
        if item.active
    ]


def _render_summary_item(item: WatchlistItem) -> None:
    with st.container(border=True):
        st.subheader(item.ticker)
        if item.state != WatchlistItemState.READY:
            st.warning(item.message or "저장된 데이터 없음")
            return
        evaluation = item.evaluation
        analysis = item.reference_analysis
        assert evaluation is not None and analysis is not None
        st.caption(analysis.company_name)
        labels = _status_labels(item)
        if labels:
            st.caption(" · ".join(labels))
        st.write(f"Case: `{analysis.case.value}`")
        st.metric(
            "평가에 사용한 종가",
            f"{evaluation.price:,.2f} {evaluation.currency}",
        )
        st.caption(
            f"거래일 {evaluation.price_session_date.isoformat()} · {evaluation.price_basis.value.upper()}"
        )
        left, right = st.columns(2)
        left.metric(
            "투자등급",
            _investment_grade(evaluation.investment_grade_result.final_grade),
        )
        right.metric("기업등급", _value(analysis.quant.grade))
        st.write(
            f"정책: `{evaluation.investment_grade_policy_version.value}` · "
            f"실행 모델: `{evaluation.investment_grade_result.model_version}`"
        )
        st.write(f"Expectation Gap: **{_expectation_gap(evaluation)}**")
        if evaluation.unresolved_reasons:
            st.warning(
                "판단 보류: "
                + " · ".join(_reason_label(reason) for reason in evaluation.unresolved_reasons)
            )
        st.caption(f"평가 시각 {evaluation.assessment_as_of.isoformat()}")


def _render_judgement(item: WatchlistItem) -> None:
    evaluation = item.evaluation
    analysis = item.reference_analysis
    assert evaluation is not None and analysis is not None

    st.subheader("판단 요약")
    left, right = st.columns(2)
    left.metric(
        "투자등급",
        _investment_grade(evaluation.investment_grade_result.final_grade),
    )
    right.metric("기업등급", _value(analysis.quant.grade))
    st.caption(
        "원본 분석을 수정한 새 분석이 아니라, 저장된 분석과 가정을 보존한 별도 파생 평가입니다."
    )
    source_grade = (
        _investment_grade(analysis.investment_grade.final_grade, show_code=True)
        if analysis.investment_grade is not None
        else "미제공"
    )
    st.write(f"원본 AnalysisSnapshot 투자등급: **{source_grade}**")
    if evaluation.investment_grade_result.final_grade.value == "U":
        st.caption("파생 투자등급 기술 코드: U")
    if evaluation.unresolved_reasons:
        st.warning(
            "판단 보류 사유: "
            + " · ".join(_reason_label(reason) for reason in evaluation.unresolved_reasons)
        )
        with st.expander("미해결 사유 코드", expanded=False):
            for reason in evaluation.unresolved_reasons:
                st.write(f"- {_reason_label(reason)} · `{reason}`")
    adjustments = _active_adjustments(evaluation)
    if adjustments:
        st.write("활성 gate / cap")
        for adjustment in adjustments:
            st.write(f"- {adjustment}")
    elif not evaluation.unresolved_reasons:
        st.write("활성 gate / cap: 없음")


def _render_business(item: WatchlistItem) -> None:
    analysis = item.reference_analysis
    assert analysis is not None
    st.subheader("사업 분석")
    st.write(
        f"기업등급: **{_value(analysis.quant.grade)}** · "
        f"기업점수 {_number(analysis.quant.score)} · "
        f"상태 `{analysis.quant.state.value}`"
    )
    with st.expander("Core 지표", expanded=True):
        for metric in analysis.quant.metrics:
            role = "Core" if metric.is_core else "Supporting"
            shown_value = _value(metric.value)
            unit = f" {metric.unit}" if metric.unit else ""
            grade = _value(metric.grade)
            st.write(
                f"**{metric.name}** — {shown_value}{unit} · 등급 {grade} · "
                f"{role} · 상태 {metric.state.value}"
            )
            if metric.note:
                st.caption(metric.note)

    current = analysis.current_trend
    if current is None:
        st.info(
            "Current Trend: 미제공 / 미해결 · Funding Stress, Commercial Inflection, "
            "Commercial Deterioration = UNKNOWN"
        )
    else:
        with st.expander("Current Trend", expanded=False):
            st.write(f"Overall: **{current.overall.value}**")
            for signal in current.signals:
                st.write(f"- {signal.name}: {signal.state.value}")
            flag_states = {item.flag: item.state for item in current.flag_results}
            for flag in TrendFlag:
                state = flag_states.get(flag, BinaryEvidenceState.UNKNOWN)
                st.write(f"- {flag.value}: {state.value.upper()}")

    narrative = analysis.narrative
    if narrative is None:
        st.info("Narrative: 미제공 / 미해결")
    else:
        with st.expander("Narrative", expanded=False):
            st.write(f"Overall: **{narrative.overall.value}**")
            for assessment in narrative.assessments:
                st.write(f"- {assessment.dimension}: {assessment.state.value}")

    if analysis.thesis_status is None:
        st.info("Thesis / KPI: 미제공 / 미해결")
    else:
        with st.expander("Thesis / KPI", expanded=False):
            st.json(analysis.thesis_status.model_dump(mode="json"), expanded=False)


def _render_valuation(item: WatchlistItem) -> None:
    evaluation = item.evaluation
    assert evaluation is not None
    st.subheader("가격과 Valuation")
    st.write(
        f"평가에 사용한 종가: **{evaluation.price:,.2f} {evaluation.currency}** · "
        f"{evaluation.price_session_date.isoformat()} · {evaluation.price_basis.value.upper()}"
    )
    st.write(f"가정: `{_assumption_label(evaluation)}`")
    valuation = evaluation.valuation_result
    if valuation is None:
        st.info(
            "가치평가: 미제공 / 미해결 · "
            + (
                " · ".join(
                    _reason_label(reason) for reason in evaluation.unresolved_reasons
                )
                or "승인된 가정이 없습니다."
            )
        )
        return
    output = valuation.output
    st.write(f"Required Growth: **{_number(output.required_growth, 4)}**")
    st.write(f"Expectation Gap: **{output.expectation_gap.value}**")
    st.write(
        "Bear / Base / Bull: "
        f"{_number(output.bear_value)} / {_number(output.base_value)} / {_number(output.bull_value)}"
    )
    st.write(f"Valuation Confidence: **{output.confidence.value}**")


def _render_evidence(item: WatchlistItem) -> None:
    evaluation = item.evaluation
    analysis = item.reference_analysis
    assert evaluation is not None and analysis is not None
    with st.expander("근거와 버전", expanded=False):
        st.write(f"Analysis ID: `{analysis.snapshot_id}`")
        st.write(f"Evaluation ID: `{evaluation.evaluation_id}`")
        st.write(f"재무 기간: `{evaluation.financial_period_label}`")
        st.write(f"재무 공개 시각: `{evaluation.financial_available_at.isoformat()}`")
        st.write(f"원본 분석 as_of: `{evaluation.original_analysis_as_of.isoformat()}`")
        st.write(f"파생 평가 as_of: `{evaluation.assessment_as_of.isoformat()}`")
        st.write(
            f"정책: `{evaluation.investment_grade_policy_version.value}` / "
            f"`{evaluation.investment_grade_result.model_version}`"
        )
        st.write(f"재무 단위: `{_value(evaluation.financial_unit)}`")
        st.write(f"회계 범위: `{_value(evaluation.accounting_scope)}`")
        st.write(f"주식수 기준: `{_value(evaluation.share_basis_version)}`")
        st.write(f"평가 생성 시각: `{evaluation.created_at.isoformat()}`")


def _render_comparison(item: WatchlistItem) -> None:
    st.subheader("이전 평가와 비교")
    diff = item.latest_diff
    if diff is None:
        st.info("이전 비교 없음 · 비교 미해결")
        return
    st.write(f"변화 유형: **{diff.change_type.value}**")
    st.write(
        f"평가 종가: {_number(diff.previous_price)} → {_number(diff.current_price)} "
        f"({diff.price_return:+.2%})"
    )
    st.write(
        "투자등급: "
        f"{_investment_grade(diff.previous_grade, show_code=True)} → "
        f"{_investment_grade(diff.current_grade, show_code=True)}"
    )
    st.write(
        f"Expectation Gap: {diff.previous_expectation_gap} → {diff.current_expectation_gap}"
    )
    if diff.unresolved_reasons:
        st.warning(
            "현재 판단 보류: "
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
        "데이터 생성은 이 화면이 아니라 기존 제한 운영 CLI에서 수행합니다. "
        "docs/limited-operating-flow.md를 확인하세요."
    )


def main() -> None:
    st.set_page_config(
        page_title="Youngrich 저장 분석 조회",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
        [data-testid="stMetricValue"] { font-size: 1.45rem; }
        [data-testid="stMarkdownContainer"], [data-testid="stMetric"] {
          overflow-wrap: anywhere;
        }
        @media (max-width: 430px) {
          .block-container { padding-left: .85rem; padding-right: .85rem; }
          [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
          [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width: 100% !important; width: 100% !important; flex: 1 1 100% !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("관심종목 저장 결과")
    st.caption("STRL · TEM · LPTH / 로컬 저장본 읽기 전용")
    st.button("저장 결과 다시 읽기", type="secondary")

    db_path, artifact_path = configured_paths()
    try:
        snapshot = load_watchlist(db_path, artifact_path)
    except WatchlistDataError as error:
        _render_load_error(error)
        return

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
        "투자등급: 이 평가에 사용한 가격에서의 투자 매력 · "
        "기업등급: 성장·수익·재무 상태"
    )

    st.subheader("요약")
    columns = st.columns(len(SUPPORTED_TICKERS))
    for column, item in zip(columns, snapshot.items, strict=True):
        with column:
            _render_summary_item(item)

    ready_tickers = [
        item.ticker for item in snapshot.items if item.state == WatchlistItemState.READY
    ]
    if not ready_tickers:
        st.info("상세히 볼 수 있는 저장 평가가 없습니다.")
        return

    selected = st.selectbox("상세 종목", ready_tickers)
    item = snapshot.item_for(selected)
    st.divider()
    st.header(f"{selected} 상세")
    _render_judgement(item)
    _render_business(item)
    _render_valuation(item)
    _render_evidence(item)
    _render_comparison(item)



if __name__ == "__main__":
    main()
