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

import pytest
from streamlit.testing.v1 import AppTest

from app.read_only_watchlist import ARTIFACT_ENV, DB_ENV, _reason_label, _status_labels
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
from engine.tracking_models import InvestmentGrade, InvestmentGradePolicyVersion


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
    assert "검증용 가정" in text
    assert all(ticker in text for ticker in ("STRL", "TEM", "LPTH"))
    assert "123.45 USD" in text
    assert "51.25 USD" in text
    assert "7.89 USD" in text
    assert "평가에 사용한 종가" in text
    assert "investment-grade-v1.1-safety" in text
    assert "저장 결과 다시 읽기" in [button.label for button in app.button]
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

    metrics = [(metric.label, metric.value) for metric in app.metric]
    assert metrics[:3] == [
        ("평가에 사용한 종가", "123.45 USD"),
        ("투자등급", "판단 보류"),
        ("기업등급", "A"),
    ]


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
    assert "파생 투자등급 기술 코드: U" in text
    assert "저장 데이터 오류" not in text


def test_display_state_comes_from_data_and_assumption_provenance(stored_watchlist):
    db_path, artifacts = stored_watchlist
    snapshot = load_watchlist(db_path, artifacts)
    strl = snapshot.item_for("STRL")
    tem = snapshot.item_for("TEM")

    assert _status_labels(strl) == ("예시 데이터",)
    assert _status_labels(tem) == ("예시 데이터", "검증용 가정")

    stored_strl = strl.model_copy(
        update={"price_snapshot": strl.price_snapshot.model_copy(update={"source": "TIINGO"})}
    )
    stored_tem = tem.model_copy(
        update={"price_snapshot": tem.price_snapshot.model_copy(update={"source": "TIINGO"})}
    )
    assert _status_labels(stored_strl) == ("검증 데이터",)
    assert _status_labels(stored_tem) == ("검증용 가정",)


def test_missing_current_and_narrative_preserve_unknown(stored_watchlist, monkeypatch):
    db_path, artifacts = stored_watchlist
    app = _run_app(monkeypatch, db_path, artifacts)
    text = _app_text(app)

    assert "Current Trend: 미제공 / 미해결" in text
    assert "Funding Stress, Commercial Inflection, Commercial Deterioration = UNKNOWN" in text
    assert "Narrative: 미제공 / 미해결" in text


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
    assert "원본 분석을 수정한 새 분석이 아니라" in text
    assert "valuation_confidence" in text
    assert "상한 B" in text


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
    assert _digest(db_path) == before_db
    assert _digest(artifacts) == before_artifacts

    _append_evaluation(db_path, artifacts, "STRL", date(2026, 9, 5), 130.00, "later")
    app.button[0].click().run()
    assert not app.exception
    assert "130.00 USD" in _app_text(app)


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
