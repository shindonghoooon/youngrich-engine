"""Categorical Case 2 Narrative Gate derivation without research or scoring."""

from __future__ import annotations

from engine.case2_policy import derive_narrative_gate
from engine.tracking_models import (
    FrozenDomainModel,
    NarrativeGate,
    NarrativeSnapshot,
)


class NarrativeGateResult(FrozenDomainModel):
    snapshot_id: str
    gate: NarrativeGate
    thesis_breaker_triggered: bool


def derive_gate_from_snapshot(
    snapshot: NarrativeSnapshot,
    *,
    commercial_evidence_exists: bool,
    thesis_breaker_triggered: bool,
    core_evidence_damaged: bool = False,
) -> NarrativeGateResult:
    axes = {assessment.dimension: assessment.state for assessment in snapshot.assessments}
    required = {"differentiation", "defensibility", "adoption", "durability"}
    missing = required - axes.keys()
    if missing:
        raise ValueError(f"NarrativeSnapshot is missing gate axes: {sorted(missing)}")
    gate = derive_narrative_gate(
        differentiation=axes["differentiation"],
        defensibility=axes["defensibility"],
        adoption=axes["adoption"],
        durability=axes["durability"],
        commercial_evidence_exists=commercial_evidence_exists,
        thesis_breaker_triggered=thesis_breaker_triggered,
        core_evidence_damaged=core_evidence_damaged,
    )
    return NarrativeGateResult(
        snapshot_id=snapshot.snapshot_id,
        gate=gate,
        thesis_breaker_triggered=thesis_breaker_triggered,
    )
