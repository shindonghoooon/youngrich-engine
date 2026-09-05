from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from engine.calibration_models import CalibrationDataQuality
from engine.research_data import (
    HistoricalInputEnvelope,
    HistoricalSecurityCandidate,
    HistoricalUniverseSnapshot,
    PilotSamplePlan,
    ResearchDataFailure,
    ResearchDataFailureReason,
    ResearchDataResult,
    StressSetResult,
    deterministic_sample,
    load_pilot_manifest,
)
from engine.tracking_models import ResolutionState


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "research_data"
    / "m12_b0_manifest.json"
)
UTC = timezone.utc


def candidate(permanent_id: str, *, anchor: date = date(2018, 12, 31)):
    return HistoricalSecurityCandidate(
        permanent_id=permanent_id,
        company_id=f"company-{permanent_id}",
        instrument_id=f"instrument-{permanent_id}",
        ticker=permanent_id,
        exchange="TEST",
        anchor_date=anchor,
        listing_start=date(2010, 1, 1),
    )


def test_deterministic_sample_is_order_independent_and_without_replacement():
    values = tuple(candidate(str(index)) for index in range(10))
    plan = PilotSamplePlan(
        seed="youngrich-m12-b0-free-first",
        version="sha256-permanent-security-id-v1",
        maximum_size=4,
    )
    first = deterministic_sample(values, plan)
    second = deterministic_sample(tuple(reversed(values)), plan)

    assert [item.permanent_id for item in first] == [
        item.permanent_id for item in second
    ]
    assert len(first) == 4
    assert len({item.permanent_id for item in first}) == 4


def test_deterministic_sample_rejects_duplicate_permanent_identity():
    plan = PilotSamplePlan(seed="seed", version="v1", maximum_size=2)
    with pytest.raises(ValueError, match="duplicate permanent"):
        deterministic_sample((candidate("same"), candidate("same")), plan)


def test_universe_contract_rejects_candidates_from_another_anchor():
    with pytest.raises(ValidationError, match="universe anchor"):
        HistoricalUniverseSnapshot(
            anchor_date=date(2018, 12, 31),
            universe_version="fixture-v1",
            candidates=(candidate("one", anchor=date(2021, 12, 31)),),
        )


def test_historical_input_envelope_rejects_look_ahead():
    with pytest.raises(ValidationError, match="available_at"):
        HistoricalInputEnvelope[dict[str, str]](
            permanent_id="security-1",
            case="case1_profitable_growth",
            period_end=date(2018, 12, 31),
            available_at=datetime(2019, 3, 2, tzinfo=UTC),
            analysis_as_of=datetime(2019, 3, 1, tzinfo=UTC),
            normalized_input={"fixture": "normalized"},
        )


def test_unresolved_provider_result_cannot_silently_contain_a_value():
    failure = ResearchDataFailure(
        reason=ResearchDataFailureReason.UNIVERSE_MEMBERSHIP_UNAVAILABLE,
        stage="historical_universe",
        detail="current directory is not point-in-time",
    )
    with pytest.raises(ValidationError, match="no value"):
        ResearchDataResult[str](
            quality=CalibrationDataQuality.UNRESOLVED,
            value="pretend-zero-or-empty-universe",
            failures=(failure,),
        )


def test_outcome_aware_stress_sample_cannot_enter_calibration_cohort():
    with pytest.raises(ValidationError, match="cannot enter calibration cohort"):
        StressSetResult(
            sample_id="stress",
            event_type="reverse_split",
            analysis_state=ResolutionState.UNRESOLVED,
            performance_state=ResolutionState.UNRESOLVED,
            calibration_cohort=True,
            unresolved_reasons=(ResearchDataFailureReason.CORPORATE_ACTION_UNSAFE,),
            note="fixture",
        )


def test_b0_manifest_preserves_all_failures_and_zero_cohort_output():
    manifest = load_pilot_manifest(FIXTURE)

    assert [item.anchor_year for item in manifest.anchors] == [2018, 2021, 2022]
    assert sum(item.discovery_records_returned for item in manifest.anchors) == 300
    assert sum(item.validated_security_candidates for item in manifest.anchors) == 0
    assert manifest.cohort_records_produced == 0
    assert all(not item.calibration_cohort for item in manifest.stress_set)
    assert manifest.verdict.value == "fail"
