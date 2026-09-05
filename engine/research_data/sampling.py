"""Deterministic sampling after point-in-time universe membership is established."""

from __future__ import annotations

from hashlib import sha256

from pydantic import Field

from engine.research_data.contracts import HistoricalSecurityCandidate
from engine.tracking_models import FrozenDomainModel


class PilotSamplePlan(FrozenDomainModel):
    seed: str
    version: str
    maximum_size: int = Field(gt=0, le=200)


def _rank(candidate: HistoricalSecurityCandidate, plan: PilotSamplePlan) -> str:
    value = f"{plan.version}\0{plan.seed}\0{candidate.permanent_id}"
    return sha256(value.encode("utf-8")).hexdigest()


def deterministic_sample(
    candidates: tuple[HistoricalSecurityCandidate, ...],
    plan: PilotSamplePlan,
) -> tuple[HistoricalSecurityCandidate, ...]:
    """Return a stable, no-replacement sample independent of provider ordering."""
    identities = [item.permanent_id for item in candidates]
    if len(identities) != len(set(identities)):
        raise ValueError("cannot sample duplicate permanent security identities")
    return tuple(sorted(candidates, key=lambda item: (_rank(item, plan), item.permanent_id))[
        : plan.maximum_size
    ])
