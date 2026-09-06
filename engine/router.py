from __future__ import annotations

from dataclasses import dataclass
from engine.models import CaseType


IMPLEMENTED_CASES = frozenset(
    {CaseType.PROFITABLE_GROWTH, CaseType.LOSS_MAKING_GROWTH}
)


@dataclass
class RouterInput:
    profitable: bool
    recent_operating_loss: bool = False
    structurally_cyclical: bool = False
    high_roic_long_duration: bool = False
    mature_slow_growth: bool = False
    asset_or_event_driven: bool = False


def route_case(x: RouterInput) -> CaseType | None:
    '''
    Minimal placeholder router.

    The router intentionally stays simple until all six case definitions
    are validated. Rule order reflects economic structure, not sector labels.
    '''
    if x.asset_or_event_driven:
        return CaseType.ASSET_SPECIAL
    if x.structurally_cyclical:
        return CaseType.CYCLICAL
    if x.recent_operating_loss:
        return CaseType.LOSS_MAKING_GROWTH
    if x.mature_slow_growth:
        return CaseType.LARGECAP_VALUE
    # TODO: Calibrate the boundary with Profitable Growth using a broader
    # sample. Until then, do not auto-promote the ambiguous input to the
    # unimplemented Quality Compounder case.
    if x.high_roic_long_duration:
        return None
    if x.profitable:
        return CaseType.PROFITABLE_GROWTH
    return None


def require_implemented_case(x: RouterInput) -> CaseType:
    """Resolve an executable Case or block unresolved/unimplemented routes."""
    case = route_case(x)
    if case is None:
        raise ValueError("Case Router result is unresolved")
    if case not in IMPLEMENTED_CASES:
        raise NotImplementedError(f"{case.value} is not implemented")
    return case
