from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from app.read_only_watchlist import (
    ACCESSIBLE_COLOR_PAIRS,
    APP_CSS,
    ARTIFACT_ENV,
    DB_ENV,
    _case_label,
    _direction_label,
    _metric_label,
    _metric_rows,
    _metric_status,
    _metric_value,
    _reason_detail,
    _reason_label,
    _reason_requirement,
    _reason_sentence,
    _status_labels,
    _summary_card_html,
)
from engine.limited_operating import (
    LimitedOperatingService,
    exact_us_close_snapshot,
    load_demo_profile,
)
from engine.persistence.models import Base
from engine.persistence.session import create_session_factory, create_sqlite_engine
from engine.read_only_watchlist import (
    WatchlistDataError,
    WatchlistErrorCode,
    WatchlistItemState,
    load_watchlist,
)
from engine.research_data.tiingo import TiingoClient
from engine.tracking_models import (
    InvestmentGrade,
    InvestmentGradePolicyVersion,
    ResolutionState,
)


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "read_only_watchlist.py"
UTC = timezone.utc


def _raw_close(ticker: str, session_date: date, close: float, suffix: str):
    profile = load_demo_profile(ROOT, ticker)
    return exact_us_close_snapshot(
        ticker=ticker,
        company_id=profile.company_id,
        session_date=session_date,
        close=close,
        retrieved_at=datetime(2026, 9, 6, 12, tzinfo=UTC),
        source="SYNTHETIC_TEST_ONLY",
        provider_reference="offline pytest fixture; not market evidence",
        snapshot_id=f"watchlist-{ticker}-{session_date.isoformat()}-{suffix}",
    )


def _append_evaluation(
    db_path: Path,
    artifact_path: Path,
    ticker: str,
    session_date: date,
    close: float,
    suffix: str,
) -> None:
    engine = create_sqlite_engine(db_path)
    with create_session_factory(engine)() as session:
        service = LimitedOperatingService(
            session, repo_root=ROOT, artifact_path=artifact_path
        )
        price = _raw_close(ticker, session_date, close, suffix)
        service.store_raw_close(ticker, session_date, price)
        service.revalue(
            ticker,
            price.price_snapshot_id,
            policy_version=InvestmentGradePolicyVersion.V1_1,
            assessment_as_of=price.timestamp,
            created_at=datetime(2026, 9, 6, 12, tzinfo=UTC),
        )
    engine.dispose()


@pytest.fixture
def stored_watchlist(tmp_path: Path) -> tuple[Path, Path]:
    db_path = tmp_path / "watchlist.sqlite3"
    artifact_path = tmp_path / "evaluations.jsonl"
    engine = create_sqlite_engine(db_path)
    Base.metadata.create_all(engine)
    with create_session_factory(engine)() as session:
        service = LimitedOperatingService(
            session, repo_root=ROOT, artifact_path=artifact_path
        )
        service.seed_demo()
    engine.dispose()

    _append_evaluation(db_path, artifact_path, "STRL", date(2026, 9, 4), 123.45, "one")
    _append_evaluation(db_path, artifact_path, "TEM", date(2026, 9, 3), 50.00, "previous")
    _append_evaluation(db_path, artifact_path, "TEM", date(2026, 9, 4), 51.25, "latest")
    _append_evaluation(db_path, artifact_path, "LPTH", date(2026, 9, 4), 7.89, "one")
    return db_path, artifact_path


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative_luminance(hex_color: str) -> float:
    channels = [
        int(hex_color[index : index + 2], 16) / 255
        for index in (1, 3, 5)
    ]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _app_text(app: AppTest) -> str:
    values: list[str] = []
    for kind in (
        "title",
        "header",
        "subheader",
        "markdown",
        "caption",
        "text",
        "info",
        "warning",
        "error",
        "success",
        "metric",
    ):
        for node in getattr(app, kind):
            values.append(str(getattr(node, "label", "")))
            values.append(str(getattr(node, "value", "")))
    return "\n".join(values)


def _run_app(monkeypatch, db_path: Path, artifact_path: Path) -> AppTest:
    monkeypatch.setenv(DB_ENV, str(db_path))
    monkeypatch.setenv(ARTIFACT_ENV, str(artifact_path))
    monkeypatch.delenv("TIINGO_API_TOKEN", raising=False)
    app = AppTest.from_file(APP, default_timeout=10)
    app.run()
    assert not app.exception
    return app


def test_missing_sources_are_distinct_and_never_created(tmp_path: Path):
    db_path = tmp_path / "missing.sqlite3"
    artifacts = tmp_path / "missing.jsonl"

    with pytest.raises(WatchlistDataError) as missing_db:
        load_watchlist(db_path, artifacts)
    assert missing_db.value.code == WatchlistErrorCode.MISSING_DATABASE
    assert not db_path.exists()
    assert not artifacts.exists()


def test_missing_sources_show_setup_guidance_without_creating_files(
    tmp_path: Path, monkeypatch
):
    db_path = tmp_path / "missing.sqlite3"
    artifacts = tmp_path / "missing.jsonl"
    app = _run_app(monkeypatch, db_path, artifacts)
    text = _app_text(app)

    assert "저장된 데이터 없음" in text
    assert "docs/limited-operating-flow.md" in text
    assert not db_path.exists()
    assert not artifacts.exists()

    sqlite3.connect(db_path).close()
    with pytest.raises(WatchlistDataError) as missing_jsonl:
        load_watchlist(db_path, artifacts)
    assert missing_jsonl.value.code == WatchlistErrorCode.MISSING_EVALUATIONS
    assert not artifacts.exists()


def test_app_loads_without_token_and_shows_stored_three_ticker_bundle(
    stored_watchlist, monkeypatch
):
    db_path, artifacts = stored_watchlist
    app = _run_app(monkeypatch, db_path, artifacts)
    text = _app_text(app)

    assert "예시 데이터" in text
    assert "검증 데이터" in text
    assert "검증용 가정" in text
    assert "아직 승인 전인 가치평가 입력" in text
    assert all(ticker in text for ticker in ("STRL", "TEM", "LPTH"))
    assert "123.45 USD" in text
    assert "51.25 USD" in text
    assert "7.89 USD" in text
    assert "평가에 사용한 가격" in text
    assert "investment-grade-v1.1-safety" in text
    assert "저장본 다시 불러오기" in [button.label for button in app.button]
    assert "투자등급" in text
    assert "기업등급" in text
    assert "투자등급: 이 평가에 사용한 가격에서의 투자 매력" in text
    assert "기업등급: 성장·수익·재무 상태" in text
    assert "Quant Grade" not in text
    assert "Investment Grade" not in text
    assert "투자 추천" not in text
    assert "종목 추천" not in text
    assert "투자 책임" not in text
    assert "참고용" not in text

    assert "가치평가 가정이 없습니다." in text
    metrics = [(metric.label, metric.value) for metric in app.metric]
    assert metrics[:3] == [
        ("기업등급", "A"),
        ("기업점수", "3.65"),
        ("계산 상태", "계산 완료"),
    ]


def test_internal_metric_codes_are_presented_as_readable_korean_values():
    growth = SimpleNamespace(name="revenue_growth", value=0.0628327228, unit="ratio")
    runway = SimpleNamespace(name="runway", value=6.1003034, unit="months")
    burn = SimpleNamespace(
        name="cash_burn_trend",
        value=4.7731837,
        unit="burn_change_ratio_or_transition",
    )

    assert _metric_label(growth.name) == "매출 성장률"
    assert _metric_value(growth) == "+6.3%"
    assert _metric_value(runway) == "6.1개월"
    assert _metric_value(burn) == "4.77배"


def test_formatter_registry_preserves_semantics_zero_and_none():
    margin = SimpleNamespace(name="margin_trend", value=1.25, unit="pct_point")
    gross_margin = SimpleNamespace(
        name="gross_margin_trend", value=0.0024, unit="pct_point"
    )
    zero_growth = SimpleNamespace(name="revenue_growth", value=0.0, unit="ratio")
    unknown_ratio = SimpleNamespace(name="custom_ratio", value=0.5, unit="ratio")
    transition = SimpleNamespace(
        name="cash_burn_trend",
        value="positive_to_burning",
        unit="burn_change_ratio_or_transition",
    )
    missing = SimpleNamespace(name="runway", value=None, unit="months")

    assert _metric_value(margin) == "+1.25%p"
    assert _metric_value(gross_margin) == "+0.24%p"
    assert _metric_value(zero_growth) == "+0.0%"
    assert _metric_value(unknown_ratio) == "0.5"
    assert _metric_value(transition) == "잉여현금흐름 흑자에서 현금 소진으로 전환"
    assert _metric_value(missing) == "자료 부족"


def test_core_supporting_unresolved_and_not_applicable_are_distinct():
    supporting = SimpleNamespace(
        name="gross_margin_trend",
        value=0.01,
        unit="pct_point",
        grade=None,
        state=ResolutionState.RESOLVED,
        is_core=False,
    )
    unresolved_core = SimpleNamespace(
        name="revenue_growth",
        value=None,
        unit=None,
        grade=None,
        state=ResolutionState.UNRESOLVED,
        is_core=True,
    )
    not_applicable = SimpleNamespace(
        name="potential_dilution",
        value="not_applicable",
        unit=None,
        grade=None,
        state=ResolutionState.RESOLVED,
        is_core=False,
    )

    assert _metric_status(supporting) == "참고 지표 · 등급 미부여"
    assert _metric_status(unresolved_core) == "자료 부족"
    assert _metric_status(not_applicable) == "적용 대상 아님"
    rows = _metric_rows(
        (supporting,),
        period_label="종료 2026-06-30",
        include_grade=False,
    )
    assert rows == [
        {
            "지표": "매출총이익률 변화",
            "값": "+1.00%p",
            "상태": "참고 지표 · 등급 미부여",
            "평가기간": "종료 2026-06-30",
        }
    ]


def test_display_formatting_never_mutates_raw_metric_value():
    metric = SimpleNamespace(name="revenue_growth", value=0.0628327228, unit="ratio")
    original = metric.value

    assert _metric_value(metric) == "+6.3%"
    assert metric.value == original


def test_user_labels_keep_case_grade_and_trend_as_separate_axes():
    assert _case_label("case1_profitable_growth") == "Case 1 · 흑자 성장"
    assert (
        _case_label("case2_emerging_asymmetric_growth")
        == "Case 2 · 비대칭 성장"
    )
    assert _direction_label("positive") == "개선"
    assert _direction_label("neutral") == "보합"
    assert _direction_label("negative") == "악화"


def test_valid_u_is_not_presented_as_a_data_error(stored_watchlist, monkeypatch):
    db_path, artifacts = stored_watchlist
    snapshot = load_watchlist(db_path, artifacts)
    strl = snapshot.item_for("STRL")
    lpth = snapshot.item_for("LPTH")

    assert strl.state == WatchlistItemState.READY
    assert strl.evaluation.investment_grade_result.final_grade == InvestmentGrade.U
    assert "VALUATION_ASSUMPTIONS_UNAVAILABLE" in strl.evaluation.unresolved_reasons
    assert lpth.state == WatchlistItemState.READY
    assert "VALUATION_COMBINATION_UNRESOLVED" in lpth.evaluation.unresolved_reasons

    app = _run_app(monkeypatch, db_path, artifacts)
    text = _app_text(app)
    assert "VALUATION_ASSUMPTIONS_UNAVAILABLE" in text
    assert "가치평가 가정 없음" in text
    assert "판단 보류" in text
    assert "파생 투자등급 기술 코드" in text
    assert "저장 데이터 오류" not in text


def test_strl_and_lpth_unresolved_reasons_are_plain_and_not_invented(
    stored_watchlist, monkeypatch
):
    db_path, artifacts = stored_watchlist
    snapshot = load_watchlist(db_path, artifacts)
    strl = snapshot.item_for("STRL")
    lpth = snapshot.item_for("LPTH")

    assert _reason_sentence("VALUATION_ASSUMPTIONS_UNAVAILABLE") == (
        "가치평가 가정이 없습니다."
    )
    assert _reason_requirement("VALUATION_ASSUMPTIONS_UNAVAILABLE") == (
        "가치평가 가정"
    )
    assert _reason_sentence("VALUATION_COMBINATION_UNRESOLVED") == (
        "평가 조건 확인이 필요합니다."
    )
    assert _reason_detail("VALUATION_COMBINATION_UNRESOLVED") == (
        "저장된 세부 원인 정보 없음"
    )
    assert "가치평가 가정이 없습니다." in _summary_card_html(strl)
    assert "평가 조건 확인이 필요합니다." in _summary_card_html(lpth)

    app = _run_app(monkeypatch, db_path, artifacts)
    app.selectbox[0].select("LPTH").run()
    text = _app_text(app)
    assert "상세 원인" in text
    assert "저장된 세부 원인 정보 없음" in text
    assert "자금 부족" not in text
    assert "고객 부족" not in text


def test_summary_card_keeps_human_date_and_hides_diagnostic_identifiers(
    stored_watchlist,
):
    db_path, artifacts = stored_watchlist
    item = load_watchlist(db_path, artifacts).item_for("STRL")
    html = _summary_card_html(item)

    assert "2026-09-04 종가" in html
    assert "Case 1 · 흑자 성장" in html
    assert "판단 보류" in html
    assert "investment-grade-v1.1-safety" not in html
    assert item.evaluation.evaluation_id not in html
    assert item.evaluation.assessment_as_of.isoformat() not in html


def test_display_state_comes_from_data_and_assumption_provenance(stored_watchlist):
    db_path, artifacts = stored_watchlist
    snapshot = load_watchlist(db_path, artifacts)
    strl = snapshot.item_for("STRL")
    tem = snapshot.item_for("TEM")

    assert _status_labels(strl) == ("예시 데이터", "검증 데이터")
    assert _status_labels(tem) == (
        "예시 데이터",
        "검증 데이터",
        "검증용 가정",
    )

    stored_strl = strl.model_copy(
        update={"price_snapshot": strl.price_snapshot.model_copy(update={"source": "TIINGO"})}
    )
    stored_tem = tem.model_copy(
        update={"price_snapshot": tem.price_snapshot.model_copy(update={"source": "TIINGO"})}
    )
    assert _status_labels(stored_strl) == ("검증 데이터",)
    assert _status_labels(stored_tem) == (
        "검증 데이터",
        "검증용 가정",
    )


def test_missing_current_and_narrative_preserve_unknown(stored_watchlist, monkeypatch):
    db_path, artifacts = stored_watchlist
    app = _run_app(monkeypatch, db_path, artifacts)
    text = _app_text(app)

    assert "저장된 최근 비교 자료가 없어 추세를 확인할 수 없습니다." in text
    assert "비교기간 정보 없음" in text
    assert "자금 부담 · 상업화 전환 · 사업 악화 상태: 미확인" in text
    assert "사업 근거: 저장된 평가 자료가 없습니다." in text


def test_source_v1_and_derived_v1_1_are_distinguished(stored_watchlist, monkeypatch):
    db_path, artifacts = stored_watchlist
    app = _run_app(monkeypatch, db_path, artifacts)
    app.selectbox[0].select("TEM").run()
    assert not app.exception
    text = _app_text(app)

    assert "원본 AnalysisSnapshot 투자등급" in text
    assert "투자등급" in text
    assert "기업등급" in text
    assert "investment-grade-v1.1-safety" in text
    assert "저장된 원본 분석과 가정은 그대로 두고" in text
    assert "가치평가 신뢰도" in text
    assert "상한 B" in text


def test_quant_grade_x_and_current_positive_are_preserved_as_distinct_axes(
    stored_watchlist, monkeypatch
):
    db_path, artifacts = stored_watchlist
    stored = load_watchlist(db_path, artifacts).item_for("LPTH")
    assert stored.reference_analysis.quant.grade.value == "X"
    assert stored.reference_analysis.current_trend.overall.value == "positive"

    app = _run_app(monkeypatch, db_path, artifacts)
    app.selectbox[0].select("LPTH").run()
    text = _app_text(app)

    assert "기업등급" in text
    assert "X" in text
    assert "종합 추세: 개선" in text
    assert "최근 실적 추세는 기업등급과 별도의 최근 변화 지표입니다." in text
    assert "비교기간 정보 없음" in text


def test_unknown_reason_keeps_original_code_visible(stored_watchlist, monkeypatch):
    db_path, artifacts = stored_watchlist
    _append_evaluation(
        db_path, artifacts, "STRL", date(2026, 9, 5), 124.00, "unknown-reason"
    )
    snapshot = load_watchlist(db_path, artifacts)
    original = snapshot.item_for("STRL").evaluation
    assert original is not None
    altered = original.model_copy(
        update={
            "unresolved_reasons": ("NEW_UNMAPPED_REASON",),
        }
    )
    rows = [
        (
            json.dumps(altered.model_dump(mode="json"), sort_keys=True)
            if original.evaluation_id in line
            else line
        )
        for line in artifacts.read_text(encoding="utf-8").splitlines()
    ]
    artifacts.write_text("\n".join(rows) + "\n", encoding="utf-8")

    app = _run_app(monkeypatch, db_path, artifacts)
    text = _app_text(app)
    assert _reason_label("NEW_UNMAPPED_REASON") == "기타 미해결 사유"
    assert "기타 미해결 사유" in text
    assert "NEW_UNMAPPED_REASON" in text


def test_known_grade_cap_uses_plain_korean_label():
    assert _reason_label("Valuation Confidence cap") == "가치평가 신뢰도 상한"


def test_one_evaluation_has_no_comparison_and_two_use_existing_diff(stored_watchlist):
    db_path, artifacts = stored_watchlist
    snapshot = load_watchlist(db_path, artifacts)

    assert snapshot.item_for("STRL").latest_diff is None
    tem = snapshot.item_for("TEM")
    assert tem.latest_diff is not None
    assert tem.latest_diff.previous_price == pytest.approx(50.0)
    assert tem.latest_diff.current_price == pytest.approx(51.25)
    assert tem.latest_diff.change_type.value == "PRICE_ONLY"


def test_reload_observes_append_without_mutating_sources(stored_watchlist, monkeypatch):
    db_path, artifacts = stored_watchlist
    app = _run_app(monkeypatch, db_path, artifacts)
    before_db = _digest(db_path)
    before_artifacts = _digest(artifacts)

    app.selectbox[0].select("LPTH").run()
    app.button[0].click().run()
    assert not app.exception
    assert "저장본을 다시 불러왔습니다." in _app_text(app)
    assert app.selectbox[0].value == "LPTH"
    assert _digest(db_path) == before_db
    assert _digest(artifacts) == before_artifacts

    _append_evaluation(db_path, artifacts, "STRL", date(2026, 9, 5), 130.00, "later")
    app.button[0].click().run()
    assert not app.exception
    assert "130.00 USD" in _app_text(app)


def test_render_and_reload_preserve_stored_snapshot_and_evaluation_models(
    stored_watchlist, monkeypatch
):
    db_path, artifacts = stored_watchlist
    before = load_watchlist(db_path, artifacts)
    before_models = [
        (
            item.reference_analysis.model_dump(mode="json"),
            item.evaluation.model_dump(mode="json"),
        )
        for item in before.items
        if item.reference_analysis is not None and item.evaluation is not None
    ]

    app = _run_app(monkeypatch, db_path, artifacts)
    app.selectbox[0].select("TEM").run()
    app.button[0].click().run()

    after = load_watchlist(db_path, artifacts)
    after_models = [
        (
            item.reference_analysis.model_dump(mode="json"),
            item.evaluation.model_dump(mode="json"),
        )
        for item in after.items
        if item.reference_analysis is not None and item.evaluation is not None
    ]
    assert after_models == before_models


def test_corrupt_jsonl_is_explicit_and_never_falls_back_to_old_record(
    stored_watchlist, tmp_path: Path, monkeypatch
):
    db_path, artifacts = stored_watchlist
    corrupt = tmp_path / "corrupt.jsonl"
    shutil.copyfile(artifacts, corrupt)
    with corrupt.open("a", encoding="utf-8") as stream:
        stream.write("{not valid json}\n")

    with pytest.raises(WatchlistDataError) as error:
        load_watchlist(db_path, corrupt)
    assert error.value.code == WatchlistErrorCode.CORRUPT_EVALUATIONS

    app = _run_app(monkeypatch, db_path, corrupt)
    text = _app_text(app)
    assert "저장 데이터 오류" in text
    assert "과거 기록을 표시하지 않았습니다" in text
    assert "123.45 USD" not in text


def test_missing_reference_analysis_is_distinct_from_valid_u(stored_watchlist):
    db_path, artifacts = stored_watchlist
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "DELETE FROM metric_results WHERE quant_snapshot_id = "
            "(SELECT snapshot_id FROM quant_snapshots WHERE analysis_snapshot_id = ?)",
            ("STRL-demo-analysis-2026-08-30",),
        )
        connection.execute(
            "DELETE FROM quant_snapshots WHERE analysis_snapshot_id = ?",
            ("STRL-demo-analysis-2026-08-30",),
        )
        connection.execute(
            "DELETE FROM analysis_snapshots WHERE snapshot_id = ?",
            ("STRL-demo-analysis-2026-08-30",),
        )
    snapshot = load_watchlist(db_path, artifacts)
    assert snapshot.item_for("STRL").state == WatchlistItemState.MISSING_ANALYSIS
    assert snapshot.item_for("LPTH").state == WatchlistItemState.READY


def test_render_select_reload_never_call_write_calculation_or_provider(
    stored_watchlist, monkeypatch
):
    db_path, artifacts = stored_watchlist

    def forbidden(*_args, **_kwargs):
        raise AssertionError("read-only UI crossed a write/calculation/provider boundary")

    monkeypatch.setattr(LimitedOperatingService, "seed_demo", forbidden)
    monkeypatch.setattr(LimitedOperatingService, "refresh_eod", forbidden)
    monkeypatch.setattr(LimitedOperatingService, "revalue", forbidden)
    monkeypatch.setattr(TiingoClient, "from_environment", forbidden)

    app = _run_app(monkeypatch, db_path, artifacts)
    app.selectbox[0].select("LPTH").run()
    app.button[0].click().run()
    assert not app.exception


def test_separate_process_reads_the_same_latest_evaluations(stored_watchlist):
    db_path, artifacts = stored_watchlist
    local = load_watchlist(db_path, artifacts)
    expected = ",".join(
        f"{item.ticker}:{item.evaluation.evaluation_id}"
        for item in local.items
        if item.evaluation is not None
    )
    code = (
        "import sys; from engine.read_only_watchlist import load_watchlist; "
        "s=load_watchlist(sys.argv[1],sys.argv[2]); "
        "print(','.join(f'{i.ticker}:{i.evaluation.evaluation_id}' "
        "for i in s.items if i.evaluation is not None))"
    )
    environment = os.environ.copy()
    environment.pop("TIINGO_API_TOKEN", None)
    result = subprocess.run(
        [sys.executable, "-c", code, str(db_path), str(artifacts)],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == expected


def test_invalid_paths_are_not_exposed_as_investment_u(tmp_path: Path):
    db_directory = tmp_path / "database-directory"
    jsonl_directory = tmp_path / "jsonl-directory"
    db_directory.mkdir()
    jsonl_directory.mkdir()

    with pytest.raises(WatchlistDataError) as db_error:
        load_watchlist(db_directory, jsonl_directory)
    assert db_error.value.code == WatchlistErrorCode.INVALID_DATABASE_PATH
    assert "U" not in db_error.value.public_message


def test_streamlit_usage_telemetry_is_disabled():
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "gatherUsageStats = false" in config


def test_responsive_grid_contract_covers_required_viewports():
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in APP_CSS
    assert "@media (max-width: 1199px)" in APP_CSS
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in APP_CSS
    assert "@media (max-width: 767px)" in APP_CSS
    assert ".yr-card-grid, .yr-judgement-grid" in APP_CSS
    assert "grid-template-columns: minmax(0, 1fr)" in APP_CSS
    assert "overflow-wrap: anywhere" in APP_CSS
    assert "white-space: normal" in APP_CSS


def test_declared_ui_color_pairs_meet_wcag_normal_text_contrast():
    for foreground, background in ACCESSIBLE_COLOR_PAIRS:
        assert foreground in APP_CSS
        assert background in APP_CSS
        assert _contrast_ratio(foreground, background) >= 4.5
