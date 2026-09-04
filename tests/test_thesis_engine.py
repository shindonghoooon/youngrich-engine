from datetime import date, datetime, timedelta, timezone

import pytest

from engine.thesis_engine import build_thesis_status, evaluate_kpi_direction
from engine.tracking_models import (
    AnalysisCase,
    DirectionState,
    KPIDirection,
    ResolutionState,
    ThesisDefinition,
    ThesisStatus,
    TrackingKPIDefinition,
    TrackingKPIObservation,
)


UTC = timezone.utc
AS_OF = datetime(2026, 9, 1, tzinfo=UTC)


def thesis(version=1):
    return ThesisDefinition(
        thesis_id="tem-thesis", ticker="TEM", version=version,
        case=AnalysisCase.CASE_2_EMERGING_ASYMMETRIC_GROWTH,
        title="Commercial adoption", thesis="Adoption expands", failure_mode="Adoption reverses",
        kpi_set_version=version, kpi_definition_ids=("volume", "concentration", "custom"), effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    )


def definitions(version=1):
    common = dict(ticker="TEM", thesis_id="tem-thesis", thesis_version=version, kpi_set_version=version, unit="ratio", source_requirement="official filing", confirming_condition="direction improves", weakening_condition="direction weakens")
    return (
        TrackingKPIDefinition(kpi_definition_id="volume", kpi_key="volume", name="Volume", direction=KPIDirection.HIGHER_IS_BETTER, **common),
        TrackingKPIDefinition(kpi_definition_id="concentration", kpi_key="concentration", name="Largest customer", direction=KPIDirection.LOWER_IS_BETTER, **common),
        TrackingKPIDefinition(kpi_definition_id="custom", kpi_key="custom", name="Commercial milestone", direction=KPIDirection.CUSTOM, is_primary=False, **common),
    )


def observation(identifier, key, value, *, when, version=1, state=ResolutionState.RESOLVED, interpreted=None):
    return TrackingKPIObservation(
        observation_id=identifier, ticker="TEM", kpi_definition_id=key, kpi_key=key,
        thesis_version=version, kpi_set_version=version, state=state,
        value=value if state == ResolutionState.RESOLVED else None, interpreted_direction=interpreted,
        source_reference="official fixture", period_end=when, available_at=datetime.combine(when, datetime.min.time(), tzinfo=UTC) + timedelta(days=10), as_of=AS_OF,
    )


def periods(volume_previous=100, volume_current=120, concentration_previous=0.50, concentration_current=0.40, *, version=1):
    previous_date, current_date = date(2026, 3, 31), date(2026, 6, 30)
    previous = (
        observation("p-volume", "volume", volume_previous, when=previous_date, version=version),
        observation("p-concentration", "concentration", concentration_previous, when=previous_date, version=version),
        observation("p-custom", "custom", "old", when=previous_date, version=version, interpreted=DirectionState.NEUTRAL),
    )
    current = (
        observation("c-volume", "volume", volume_current, when=current_date, version=version),
        observation("c-concentration", "concentration", concentration_current, when=current_date, version=version),
        observation("c-custom", "custom", "new", when=current_date, version=version, interpreted=DirectionState.POSITIVE),
    )
    return previous, current


def evaluate(previous, current, **kwargs):
    return build_thesis_status(snapshot_id="thesis-status", thesis=thesis(), definitions=definitions(), previous_observations=previous, current_observations=current, as_of=AS_OF, **kwargs)


def test_confirming_and_higher_is_worse_kpi():
    previous, current = periods()
    result = evaluate(previous, current)
    assert result.status == ThesisStatus.CONFIRMING
    assert evaluate_kpi_direction(definitions()[1], previous[1], current[1]) == DirectionState.POSITIVE


def test_neutral_when_primary_directions_tie():
    previous, current = periods(volume_current=120, concentration_current=0.60)
    assert evaluate(previous, current).status == ThesisStatus.NEUTRAL


def test_legacy_stable_input_is_normalized_to_neutral():
    previous, current = periods(volume_current=120, concentration_current=0.60)
    result = evaluate(previous, current)
    legacy = result.model_dump(mode="json") | {"status": "stable"}
    normalized = type(result).model_validate(legacy)
    assert normalized.status == ThesisStatus.NEUTRAL
    assert normalized.model_dump(mode="json")["status"] == "neutral"
    assert "stable" not in {status.value for status in ThesisStatus}


def test_weakening_when_primary_majority_deteriorates():
    previous, current = periods(volume_current=90, concentration_current=0.60)
    assert evaluate(previous, current).status == ThesisStatus.WEAKENING


def test_broken_has_precedence():
    previous, current = periods()
    result = evaluate(previous, current, thesis_breaker_triggered=True)
    assert result.status == ThesisStatus.BROKEN
    assert result.breaker_triggered is True


def test_unresolved_is_not_neutral_and_requires_two_primary_kpis():
    previous, current = periods()
    current = (current[0], current[1].model_copy(update={"state": ResolutionState.UNRESOLVED, "value": None}), current[2])
    assert evaluate(previous, current).status == ThesisStatus.UNRESOLVED


def test_material_narrative_deterioration_blocks_confirming():
    previous, current = periods()
    assert evaluate(previous, current, material_narrative_deterioration=True).status == ThesisStatus.NEUTRAL


def test_kpi_version_mismatch_is_rejected():
    previous, current = periods()
    invalid = current[0].model_copy(update={"kpi_set_version": 2})
    with pytest.raises(ValueError, match="KPI-set version mismatch"):
        evaluate(previous, (invalid, current[1], current[2]))


def test_observation_after_evaluation_cutoff_is_rejected():
    previous, current = periods()
    future = current[0].model_copy(update={"available_at": AS_OF + timedelta(days=1), "as_of": AS_OF + timedelta(days=1)})
    with pytest.raises(ValueError, match="after thesis as_of"):
        evaluate(previous, (future, current[1], current[2]))
