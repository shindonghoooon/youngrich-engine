from __future__ import annotations

from dataclasses import dataclass
from engine.models import CaseType


@dataclass
class RouterInput:
    profitable: bool
    recent_operating_loss: bool = False
    structurally_cyclical: bool = False
    high_roic_long_duration: bool = False
    mature_slow_growth: bool = False
    asset_or_event_driven: bool = False


def route_case(x: RouterInput) -> CaseType:
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
    if x.high_roic_long_duration and not x.profitable:
        return CaseType.QUALITY_COMPOUNDER
    if x.profitable:
        return CaseType.PROFITABLE_GROWTH
    return CaseType.QUALITY_COMPOUNDER
