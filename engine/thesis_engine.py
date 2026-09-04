"""Version-safe, categorical thesis tracking from generic KPI observations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from engine.tracking_models import (
    DirectionState,
    KPIDirection,
    ResolutionState,
    ThesisDefinition,
    ThesisStatus,
    ThesisStatusSnapshot,
    TrackingKPIDefinition,
    TrackingKPIObservation,
)


def _validate_definition(thesis: ThesisDefinition, definition: TrackingKPIDefinition) -> None:
    if definition.ticker != thesis.ticker:
        raise ValueError("KPI definition ticker must match thesis ticker")
    if definition.thesis_id != thesis.thesis_id:
        raise ValueError("KPI definition thesis_id must match thesis")
    if definition.thesis_version != thesis.version:
        raise ValueError("KPI definition thesis version mismatch")
    if definition.kpi_set_version != thesis.kpi_set_version:
        raise ValueError("KPI definition KPI-set version mismatch")
    if definition.kpi_definition_id not in thesis.kpi_definition_ids:
        raise ValueError("KPI definition is not part of the thesis KPI set")


def _validate_observation(
    thesis: ThesisDefinition,
    definition: TrackingKPIDefinition,
    observation: TrackingKPIObservation,
) -> None:
    if observation.ticker != thesis.ticker:
        raise ValueError("KPI observation ticker must match thesis ticker")
    if observation.kpi_definition_id != definition.kpi_definition_id:
        raise ValueError("KPI observation definition id mismatch")
    if observation.kpi_key != definition.kpi_key:
        raise ValueError("KPI observation key mismatch")
    if observation.thesis_version != thesis.version:
        raise ValueError("KPI observation thesis version mismatch")
    if observation.kpi_set_version != thesis.kpi_set_version:
        raise ValueError("KPI observation KPI-set version mismatch")


def evaluate_kpi_direction(
    definition: TrackingKPIDefinition,
    previous: TrackingKPIObservation,
    current: TrackingKPIObservation,
) -> DirectionState:
    if previous.state == ResolutionState.UNRESOLVED or current.state == ResolutionState.UNRESOLVED:
        return DirectionState.UNRESOLVED
    if definition.direction in {KPIDirection.CUSTOM, KPIDirection.UNRESOLVED}:
        return current.interpreted_direction or DirectionState.UNRESOLVED
    if not isinstance(previous.value, (int, float)) or not isinstance(current.value, (int, float)):
        return DirectionState.UNRESOLVED
    if current.value == previous.value:
        return DirectionState.NEUTRAL
    higher = current.value > previous.value
    improving = higher if definition.direction == KPIDirection.HIGHER_IS_BETTER else not higher
    return DirectionState.POSITIVE if improving else DirectionState.NEGATIVE


def build_thesis_status(
    *,
    snapshot_id: str,
    thesis: ThesisDefinition,
    definitions: Sequence[TrackingKPIDefinition],
    previous_observations: Sequence[TrackingKPIObservation],
    current_observations: Sequence[TrackingKPIObservation],
    as_of: datetime,
    thesis_breaker_triggered: bool = False,
    material_narrative_deterioration: bool = False,
) -> ThesisStatusSnapshot:
    if thesis.effective_from > as_of:
        raise ValueError("thesis version cannot become effective after evaluation as_of")
    definition_map = {item.kpi_definition_id: item for item in definitions}
    if len(definition_map) != len(definitions):
        raise ValueError("KPI definition ids must be unique")
    if set(definition_map) != set(thesis.kpi_definition_ids):
        raise ValueError("definitions must exactly match the thesis KPI set")
    for definition in definitions:
        _validate_definition(thesis, definition)

    previous_map = {item.kpi_definition_id: item for item in previous_observations}
    current_map = {item.kpi_definition_id: item for item in current_observations}
    if len(previous_map) != len(previous_observations) or len(current_map) != len(current_observations):
        raise ValueError("one observation per KPI definition and period is required")
    if set(previous_map) != set(definition_map) or set(current_map) != set(definition_map):
        raise ValueError("observation sets must exactly match the thesis KPI set")

    directions = []
    for definition_id, definition in definition_map.items():
        previous = previous_map[definition_id]
        current = current_map[definition_id]
        _validate_observation(thesis, definition, previous)
        _validate_observation(thesis, definition, current)
        if any(
            item.as_of > as_of or item.available_at > as_of
            for item in (previous, current)
        ):
            raise ValueError("KPI observation cannot use information after thesis as_of")
        if definition.is_primary:
            directions.append(evaluate_kpi_direction(definition, previous, current))

    resolved = [item for item in directions if item != DirectionState.UNRESOLVED]
    improving = resolved.count(DirectionState.POSITIVE) + resolved.count(DirectionState.STRONG_POSITIVE)
    deteriorating = resolved.count(DirectionState.NEGATIVE)
    if thesis_breaker_triggered:
        status = ThesisStatus.BROKEN
    elif len(resolved) < 2:
        status = ThesisStatus.UNRESOLVED
    elif deteriorating > improving:
        status = ThesisStatus.WEAKENING
    elif improving > deteriorating and not material_narrative_deterioration:
        status = ThesisStatus.CONFIRMING
    else:
        status = ThesisStatus.NEUTRAL

    latest = max(current_observations, key=lambda item: item.period_end)
    available_at = max(item.available_at for item in current_observations)
    return ThesisStatusSnapshot(
        snapshot_id=snapshot_id,
        ticker=thesis.ticker,
        thesis_id=thesis.thesis_id,
        thesis_version=thesis.version,
        kpi_set_version=thesis.kpi_set_version,
        observation_ids=tuple(item.observation_id for item in current_observations),
        status=status,
        breaker_triggered=thesis_breaker_triggered,
        material_narrative_deterioration=material_narrative_deterioration,
        note="unresolved KPI observations are excluded, never treated as neutral",
        period_end=latest.period_end,
        available_at=available_at,
        as_of=as_of,
    )
