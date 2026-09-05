from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.limited_operating import (
    EvaluationArtifactStore,
    EvaluationChangeType,
    LimitedOperatingService,
    RefreshStatus,
    UsageMode,
    WriteStatus,
    exact_us_close_snapshot,
    load_demo_profile,
)
from engine.persistence.models import Base
from engine.persistence.repositories import AnalysisRepository, PriceRepository
from engine.persistence.session import create_session_factory, create_sqlite_engine
from engine.tracking_models import (
    AsymmetryType,
    BinaryEvidenceState,
    InvestmentGrade,
    InvestmentGradePolicyVersion,
    PriceBasis,
    TrendFlag,
    TrendFlagResult,
)
from research.limited_operating_flow import main as cli_main


ROOT = Path(__file__).parents[1]
UTC = timezone.utc


@pytest.fixture
def operating(tmp_path):
    engine = create_sqlite_engine()
    Base.metadata.create_all(engine)
    with create_session_factory(engine)() as session:
        yield LimitedOperatingService(
            session,
            repo_root=ROOT,
            artifact_path=tmp_path / "evaluations.jsonl",
        )


def raw_close(
    ticker: str,
    session_date: date,
    close: float,
    *,
    suffix: str = "test",
):
    profile = load_demo_profile(ROOT, ticker)
    return exact_us_close_snapshot(
        ticker=ticker,
        company_id=profile.company_id,
        session_date=session_date,
        close=close,
        retrieved_at=datetime(2026, 9, 6, 12, tzinfo=UTC),
        source="SYNTHETIC_TEST_ONLY",
        provider_reference="offline pytest fixture; not market evidence",
        snapshot_id=f"{ticker}-raw-{session_date.isoformat()}-{suffix}",
    )


def store_and_revalue(
    service: LimitedOperatingService,
    ticker: str,
    session_date: date,
    close: float,
    *,
    suffix: str = "test",
    policy: InvestmentGradePolicyVersion = InvestmentGradePolicyVersion.V1_1,
):
    price = raw_close(ticker, session_date, close, suffix=suffix)
    service.store_raw_close(ticker, session_date, price)
    return service.revalue(
        ticker,
        price.price_snapshot_id,
        policy_version=policy,
        assessment_as_of=price.timestamp,
        created_at=datetime(2026, 9, 6, 12, tzinfo=UTC),
    )[0]


def test_three_reference_analyses_round_trip_and_seed_is_idempotent(operating):
    first = operating.seed_demo()
    second = operating.seed_demo()

    assert [item.ticker for item in first] == ["STRL", "TEM", "LPTH"]
    assert all(item.analysis_status == WriteStatus.CREATED for item in first)
    assert all(item.analysis_status == WriteStatus.ALREADY_EXISTS for item in second)
    for item in first:
        stored = AnalysisRepository(operating.session).get_analysis_snapshot(
            item.analysis_snapshot_id
        )
        assert stored == operating.profile(item.ticker).analysis
        assert item.usage_mode == UsageMode.DEMO_VALIDATION


def test_same_raw_close_import_is_idempotent(operating):
    operating.seed_demo(("TEM",))
    price = raw_close("TEM", date(2026, 9, 2), 61.0)

    first = operating.store_raw_close("TEM", date(2026, 9, 2), price)
    second = operating.store_raw_close("TEM", date(2026, 9, 2), price)

    assert first.status == RefreshStatus.STORED
    assert second.status == RefreshStatus.ALREADY_EXISTS
    assert len(
        PriceRepository(operating.session).list_price_snapshots(
            operating.profile("TEM").instrument_id
        )
    ) == 2  # original fixture close + new exact-session close


def test_new_revaluation_explicitly_uses_v1_1_while_v1_golden_is_preserved(operating):
    operating.seed_demo(("TEM", "LPTH"))
    tem_reference = AnalysisRepository(operating.session).get_analysis_snapshot(
        operating.profile("TEM").analysis.snapshot_id
    )
    lpth_reference = AnalysisRepository(operating.session).get_analysis_snapshot(
        operating.profile("LPTH").analysis.snapshot_id
    )
    assert tem_reference.investment_grade.model_version == "investment-grade-v1-frozen"
    assert tem_reference.investment_grade.final_grade == InvestmentGrade.B
    assert lpth_reference.investment_grade.model_version == "investment-grade-v1-frozen"
    assert lpth_reference.investment_grade.final_grade == InvestmentGrade.C

    tem, _ = operating.revalue(
        "TEM",
        operating.profile("TEM").baseline_price.price_snapshot_id,
        created_at=datetime(2026, 9, 6, 12, tzinfo=UTC),
    )
    lpth, _ = operating.revalue(
        "LPTH",
        operating.profile("LPTH").baseline_price.price_snapshot_id,
        created_at=datetime(2026, 9, 6, 12, tzinfo=UTC),
    )

    assert tem.investment_grade_policy_version == InvestmentGradePolicyVersion.V1_1
    assert tem.investment_grade_result.model_version == "investment-grade-v1.1-safety"
    assert lpth.investment_grade_result.model_version == "investment-grade-v1.1-safety"
    assert lpth.investment_grade_result.final_grade == InvestmentGrade.U
    assert "VALUATION_COMBINATION_UNRESOLVED" in lpth.unresolved_reasons


@pytest.mark.parametrize(
    "ticker,close,expected_grade",
    (
        ("STRL", 300.0, InvestmentGrade.U),
        ("TEM", 60.0, InvestmentGrade.B),
        ("LPTH", 9.5, InvestmentGrade.U),
    ),
)
def test_each_ticker_revalues_to_append_only_export_with_demo_usage(
    operating, ticker, close, expected_grade
):
    operating.seed_demo((ticker,))
    evaluation = store_and_revalue(
        operating, ticker, date(2026, 9, 2), close
    )
    restored = EvaluationArtifactStore(operating.artifacts.path).get(
        evaluation.evaluation_id
    )

    assert restored == evaluation
    assert evaluation.usage_mode == UsageMode.DEMO_VALIDATION
    assert evaluation.reference_analysis_snapshot_id == operating.profile(ticker).analysis.snapshot_id
    assert evaluation.price_basis == PriceBasis.RAW
    assert evaluation.fundamental_input_fingerprint
    assert evaluation.investment_grade_result.final_grade == expected_grade
    if ticker == "STRL":
        assert evaluation.valuation_result is None
        assert evaluation.investment_grade_result.final_grade == InvestmentGrade.U
        assert "VALUATION_ASSUMPTIONS_UNAVAILABLE" in evaluation.unresolved_reasons


def test_two_prices_preserve_reference_layers_and_assumptions_and_compare_price_only(operating):
    operating.seed_demo(("TEM",))
    before = AnalysisRepository(operating.session).get_analysis_snapshot(
        operating.profile("TEM").analysis.snapshot_id
    )
    first = store_and_revalue(operating, "TEM", date(2026, 9, 2), 60.0, suffix="first")
    second = store_and_revalue(operating, "TEM", date(2026, 9, 3), 61.0, suffix="second")
    after = AnalysisRepository(operating.session).get_analysis_snapshot(before.snapshot_id)
    diff = operating.compare_evaluations(first.evaluation_id, second.evaluation_id)

    assert after == before
    assert first.assumption_set_id == second.assumption_set_id
    assert first.assumption_version == second.assumption_version == 1
    assert first.fundamental_input_fingerprint == second.fundamental_input_fingerprint
    assert diff.change_type == EvaluationChangeType.PRICE_ONLY
    assert diff.assumption_identity_unchanged is True
    assert diff.fundamental_input_unchanged is True
    assert diff.previous_grade == diff.current_grade


def test_policy_change_is_never_reported_as_price_only(operating):
    operating.seed_demo(("LPTH",))
    old = store_and_revalue(
        operating,
        "LPTH",
        date(2026, 9, 2),
        9.40,
        suffix="v1",
        policy=InvestmentGradePolicyVersion.V1,
    )
    safe = store_and_revalue(
        operating,
        "LPTH",
        date(2026, 9, 3),
        9.50,
        suffix="v1_1",
        policy=InvestmentGradePolicyVersion.V1_1,
    )

    diff = operating.compare_evaluations(old.evaluation_id, safe.evaluation_id)
    assert diff.change_type == EvaluationChangeType.POLICY_CHANGE
    assert diff.policy_version_unchanged is False


def test_input_scope_change_is_never_reported_as_price_only(operating):
    operating.seed_demo(("TEM",))
    first = store_and_revalue(
        operating, "TEM", date(2026, 9, 2), 60.0, suffix="scope-first"
    )
    second = store_and_revalue(
        operating, "TEM", date(2026, 9, 3), 61.0, suffix="scope-second"
    )
    altered = second.model_copy(
        update={
            "evaluation_id": f"{second.evaluation_id}-different-unit",
            "financial_unit": "USD millions",
        }
    )
    operating.artifacts.append(altered)

    diff = operating.compare_evaluations(first.evaluation_id, altered.evaluation_id)
    assert diff.change_type == EvaluationChangeType.INPUT_SCOPE_CHANGE
    assert diff.input_scope_unchanged is False


def test_funding_stress_cap_survives_a_lower_price(operating, monkeypatch):
    profile = operating.profile("TEM")
    stressed_current = profile.analysis.current_trend.model_copy(
        update={
            "flags": profile.analysis.current_trend.flags | {TrendFlag.FUNDING_STRESS},
            "flag_results": tuple(
                TrendFlagResult(
                    flag=item.flag,
                    state=(
                        BinaryEvidenceState.YES
                        if item.flag == TrendFlag.FUNDING_STRESS
                        else item.state
                    ),
                )
                for item in profile.analysis.current_trend.flag_results
            ),
        }
    )
    stressed_analysis = profile.analysis.model_copy(
        update={"current_trend": stressed_current}
    )
    stressed_profile = profile.model_copy(
        update={
            "analysis": stressed_analysis,
            "asymmetry_type": AsymmetryType.FAVORABLE,
        }
    )
    monkeypatch.setattr(operating, "profile", lambda _ticker: stressed_profile)
    operating.seed_demo(("TEM",))

    first = store_and_revalue(operating, "TEM", date(2026, 9, 2), 20.0, suffix="high")
    lower = store_and_revalue(operating, "TEM", date(2026, 9, 3), 10.0, suffix="low")

    assert first.investment_grade_result.final_grade == InvestmentGrade.C
    assert lower.investment_grade_result.final_grade == InvestmentGrade.C
    assert any(
        item.trigger.value == "funding_stress" and item.active
        for item in lower.investment_grade_result.adjustments
    )


def test_split_basis_uncertainty_returns_u_without_mutating_reference(operating, monkeypatch):
    profile = operating.profile("TEM")
    monkeypatch.setattr(
        operating,
        "profile",
        lambda _ticker: profile.model_copy(update={"share_basis_confirmed": False}),
    )
    operating.seed_demo(("TEM",))
    evaluation = store_and_revalue(
        operating, "TEM", date(2026, 9, 2), 60.0, suffix="unresolved"
    )

    assert evaluation.valuation_result is None
    assert evaluation.investment_grade_result.final_grade == InvestmentGrade.U
    assert "SHARE_SPLIT_BASIS_UNRESOLVED" in evaluation.unresolved_reasons


def test_currency_identity_and_future_information_are_rejected(operating):
    operating.seed_demo(("TEM",))
    usd = raw_close("TEM", date(2026, 9, 2), 60.0)
    with pytest.raises(ValueError, match="currency"):
        operating.store_raw_close(
            "TEM", date(2026, 9, 2), usd.model_copy(update={"currency": "KRW"})
        )
    with pytest.raises(ValueError, match="ticker"):
        operating.store_raw_close(
            "TEM", date(2026, 9, 2), usd.model_copy(update={"ticker": "LPTH"})
        )

    operating.store_raw_close("TEM", date(2026, 9, 2), usd)
    with pytest.raises(ValueError, match="not available"):
        operating.revalue(
            "TEM",
            usd.price_snapshot_id,
            assessment_as_of=operating.profile("TEM").analysis.as_of - timedelta(days=1),
        )


def test_missing_token_and_missing_price_leave_seeded_analysis_unchanged(
    operating, monkeypatch
):
    monkeypatch.delenv("TIINGO_API_TOKEN", raising=False)
    operating.seed_demo(("TEM",))
    before = AnalysisRepository(operating.session).get_analysis_snapshot(
        operating.profile("TEM").analysis.snapshot_id
    )
    result = operating.refresh_eod("TEM", date(2026, 9, 4))

    assert result.status == RefreshStatus.PENDING_CREDENTIAL
    assert result.observation_count == 0
    with pytest.raises(ValueError, match="price snapshot is not stored"):
        operating.revalue("TEM", "missing-price")
    assert AnalysisRepository(operating.session).get_analysis_snapshot(before.snapshot_id) == before


def test_run_cli_reports_all_three_pending_without_token(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TIINGO_API_TOKEN", raising=False)
    result = cli_main(
        [
            "run",
            "--db",
            str(tmp_path / "demo.sqlite3"),
            "--artifacts",
            str(tmp_path / "evaluations.jsonl"),
            "--session-date",
            "2026-09-04",
            "--json-only",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["token_detected"] is False
    assert [item["ticker"] for item in payload["results"]] == ["STRL", "TEM", "LPTH"]
    assert {
        item["refresh"]["status"] for item in payload["results"]
    } == {"pending_credential"}


def test_artifact_reload_preserves_ids_versions_and_reasons(operating):
    operating.seed_demo(("LPTH",))
    evaluation = store_and_revalue(
        operating, "LPTH", date(2026, 9, 2), 9.5, suffix="reload"
    )
    reloaded = EvaluationArtifactStore(operating.artifacts.path).list_for_ticker("LPTH")

    assert len(reloaded) == 1
    assert reloaded[0].evaluation_id == evaluation.evaluation_id
    assert reloaded[0].assumption_set_id == evaluation.assumption_set_id
    assert reloaded[0].assumption_version == evaluation.assumption_version
    assert reloaded[0].investment_grade_policy_version == InvestmentGradePolicyVersion.V1_1
    assert reloaded[0].unresolved_reasons == evaluation.unresolved_reasons
