"""Structured comparison of immutable analysis snapshots."""

from __future__ import annotations

from math import isclose

from engine.models import Grade
from engine.tracking_models import (
    AnalysisSnapshot,
    ChangeState,
    DirectionState,
    FlagDiff,
    GradeChangeAttribution,
    GradeChangeReason,
    MetricDiff,
    NarrativeDiff,
    NarrativeState,
    ResolutionState,
    SignalDiff,
    SnapshotChange,
    SnapshotDiff,
    ThesisStatus,
    TrendFlag,
    ValuationChangeType,
)


_GRADE_ORDER = {Grade.X: 0, Grade.D: 1, Grade.C: 2, Grade.B: 3, Grade.A: 4}
_DIRECTION_ORDER = {
    DirectionState.NEGATIVE: 0,
    DirectionState.NEUTRAL: 1,
    DirectionState.POSITIVE: 2,
    DirectionState.STRONG_POSITIVE: 3,
}
_NARRATIVE_ORDER = {
    NarrativeState.WEAK: 0,
    NarrativeState.EMERGING: 1,
    NarrativeState.STRONG: 2,
    NarrativeState.PROVEN: 3,
}


def _resolution_change(previous: ResolutionState | None, current: ResolutionState | None) -> ChangeState | None:
    if previous == ResolutionState.UNRESOLVED and current == ResolutionState.RESOLVED:
        return ChangeState.RESOLVED
    if previous == ResolutionState.RESOLVED and current == ResolutionState.UNRESOLVED:
        return ChangeState.BECAME_UNRESOLVED
    if previous is None or current is None:
        return ChangeState.NOT_COMPARABLE
    return None


def _metric_diff(key, previous, current) -> MetricDiff:
    if previous is None or current is None:
        return MetricDiff(
            metric_key=key,
            previous_state=previous.state if previous else None,
            current_state=current.state if current else None,
            previous_value=previous.value if previous else None,
            current_value=current.value if current else None,
            previous_grade=previous.grade if previous else None,
            current_grade=current.grade if current else None,
            change=ChangeState.NOT_COMPARABLE,
        )
    transition = _resolution_change(previous.state, current.state)
    if transition is not None:
        change = transition
    elif previous.state == ResolutionState.UNRESOLVED:
        change = ChangeState.UNCHANGED
    elif previous.grade is not None and current.grade is not None:
        change = (
            ChangeState.IMPROVED
            if _GRADE_ORDER[current.grade] > _GRADE_ORDER[previous.grade]
            else ChangeState.DETERIORATED
            if _GRADE_ORDER[current.grade] < _GRADE_ORDER[previous.grade]
            else ChangeState.UNCHANGED
        )
    elif previous.value == current.value:
        change = ChangeState.UNCHANGED
    else:
        change = ChangeState.NOT_COMPARABLE
    return MetricDiff(
        metric_key=key,
        previous_state=previous.state,
        current_state=current.state,
        previous_value=previous.value,
        current_value=current.value,
        previous_grade=previous.grade,
        current_grade=current.grade,
        change=change,
    )


def _direction_change(previous: DirectionState | None, current: DirectionState | None) -> ChangeState:
    if previous == DirectionState.UNRESOLVED and current != DirectionState.UNRESOLVED:
        return ChangeState.RESOLVED
    if previous != DirectionState.UNRESOLVED and current == DirectionState.UNRESOLVED:
        return ChangeState.BECAME_UNRESOLVED
    if previous is None or current is None:
        return ChangeState.NOT_COMPARABLE
    if previous == current:
        return ChangeState.UNCHANGED
    if previous not in _DIRECTION_ORDER or current not in _DIRECTION_ORDER:
        return ChangeState.NOT_COMPARABLE
    return ChangeState.IMPROVED if _DIRECTION_ORDER[current] > _DIRECTION_ORDER[previous] else ChangeState.DETERIORATED


def _narrative_change(previous: NarrativeState | None, current: NarrativeState | None) -> ChangeState:
    if previous == NarrativeState.UNRESOLVED and current != NarrativeState.UNRESOLVED:
        return ChangeState.RESOLVED
    if previous != NarrativeState.UNRESOLVED and current == NarrativeState.UNRESOLVED:
        return ChangeState.BECAME_UNRESOLVED
    if previous is None or current is None:
        return ChangeState.NOT_COMPARABLE
    if previous == current:
        return ChangeState.UNCHANGED
    return ChangeState.IMPROVED if _NARRATIVE_ORDER[current] > _NARRATIVE_ORDER[previous] else ChangeState.DETERIORATED


def _price_changed(previous: AnalysisSnapshot, current: AnalysisSnapshot) -> bool:
    if previous.valuation is None or current.valuation is None:
        return False
    pairs = (
        (previous.valuation.market_price, current.valuation.market_price),
        (previous.valuation.market_cap, current.valuation.market_cap),
    )
    return any(
        left is not None and right is not None and not isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)
        for left, right in pairs
    )


def _valuation_change(previous: AnalysisSnapshot, current: AnalysisSnapshot) -> ValuationChangeType:
    if previous.valuation is None or current.valuation is None:
        return ValuationChangeType.NONE
    assumptions_changed = (
        previous.valuation.assumption_set != current.valuation.assumption_set
        or previous.valuation.fundamental_input_fingerprint
        != current.valuation.fundamental_input_fingerprint
    )
    price_changed = _price_changed(previous, current)
    output_changed = previous.valuation.output != current.valuation.output
    if assumptions_changed and price_changed:
        return ValuationChangeType.MIXED
    if assumptions_changed:
        return ValuationChangeType.ASSUMPTION_CHANGE
    if price_changed and output_changed:
        return ValuationChangeType.PRICE_ONLY
    return ValuationChangeType.NONE


def build_snapshot_diff(previous: AnalysisSnapshot, current: AnalysisSnapshot) -> SnapshotDiff:
    if previous.ticker != current.ticker:
        raise ValueError("analysis snapshots must use the same ticker")
    if current.as_of <= previous.as_of:
        raise ValueError("current analysis as_of must be later than previous as_of")

    previous_metrics = {item.name: item for item in previous.quant.metrics}
    current_metrics = {item.name: item for item in current.quant.metrics}
    metric_changes = tuple(
        _metric_diff(key, previous_metrics.get(key), current_metrics.get(key))
        for key in sorted(previous_metrics.keys() | current_metrics.keys())
    )

    previous_signals = {item.name: item.state for item in previous.current_trend.signals} if previous.current_trend else {}
    current_signals = {item.name: item.state for item in current.current_trend.signals} if current.current_trend else {}
    signal_changes = tuple(
        SignalDiff(signal_key=key, previous=previous_signals.get(key), current=current_signals.get(key), change=_direction_change(previous_signals.get(key), current_signals.get(key)))
        for key in sorted(previous_signals.keys() | current_signals.keys())
    )

    previous_axes = {item.dimension: item.state for item in previous.narrative.assessments} if previous.narrative else {}
    current_axes = {item.dimension: item.state for item in current.narrative.assessments} if current.narrative else {}
    narrative_changes = tuple(
        NarrativeDiff(dimension=key, previous=previous_axes.get(key), current=current_axes.get(key), change=_narrative_change(previous_axes.get(key), current_axes.get(key)))
        for key in sorted(previous_axes.keys() | current_axes.keys())
    )

    previous_flags = previous.current_trend.flags if previous.current_trend else frozenset()
    current_flags = current.current_trend.flags if current.current_trend else frozenset()
    flag_changes = tuple(
        FlagDiff(flag=flag, previous=flag in previous_flags, current=flag in current_flags, material=flag not in previous_flags and flag in current_flags)
        for flag in TrendFlag
        if (flag in previous_flags) != (flag in current_flags)
    )
    valuation_change = _valuation_change(previous, current)
    case_changed = previous.case != current.case
    quant_changed = previous.quant.grade != current.quant.grade
    current_changed = (
        (previous.current_trend.overall if previous.current_trend else None)
        != (current.current_trend.overall if current.current_trend else None)
    )
    narrative_changed = previous.narrative_gate != current.narrative_gate or any(item.change != ChangeState.UNCHANGED for item in narrative_changes)
    previous_thesis = previous.thesis_status.status if previous.thesis_status else None
    current_thesis = current.thesis_status.status if current.thesis_status else None
    previous_breaker = bool(previous.thesis_status and previous.thesis_status.breaker_triggered) or bool(previous.investment_grade and previous.investment_grade.thesis_breaker_active)
    current_breaker = bool(current.thesis_status and current.thesis_status.breaker_triggered) or bool(current.investment_grade and current.investment_grade.thesis_breaker_active)
    funding_changed = (TrendFlag.FUNDING_STRESS in previous_flags) != (TrendFlag.FUNDING_STRESS in current_flags)
    grade_previous = previous.investment_grade.final_grade if previous.investment_grade else None
    grade_current = current.investment_grade.final_grade if current.investment_grade else None
    grade_changed = grade_previous != grade_current

    reasons: set[GradeChangeReason] = set()
    if grade_changed:
        if case_changed:
            reasons.add(GradeChangeReason.CASE_MIGRATION)
        if quant_changed:
            reasons.add(GradeChangeReason.QUANT)
        if current_changed or any(item.change != ChangeState.UNCHANGED for item in signal_changes):
            reasons.add(GradeChangeReason.CURRENT_TREND)
        if narrative_changed:
            reasons.add(GradeChangeReason.NARRATIVE)
        if funding_changed:
            reasons.add(GradeChangeReason.FUNDING)
        if current_breaker and not previous_breaker:
            reasons.add(GradeChangeReason.THESIS_BREAKER)
        if valuation_change in {ValuationChangeType.PRICE_ONLY, ValuationChangeType.MIXED}:
            reasons.add(GradeChangeReason.PRICE)
        if valuation_change in {ValuationChangeType.ASSUMPTION_CHANGE, ValuationChangeType.MIXED}:
            reasons.add(GradeChangeReason.VALUATION_ASSUMPTION)
        if any(item.change in {ChangeState.RESOLVED, ChangeState.BECAME_UNRESOLVED} for item in metric_changes + signal_changes + narrative_changes):
            reasons.add(GradeChangeReason.DATA_RESOLUTION)
        if len(reasons) > 1:
            reasons.add(GradeChangeReason.MULTIPLE)

    material: list[str] = []
    if grade_changed:
        material.append("investment_grade")
    if quant_changed:
        material.append("quant_grade")
    if case_changed:
        material.append("case_migration")
    if previous.narrative_gate != current.narrative_gate:
        material.append("narrative_gate")
    previous_gap = previous.valuation.output.expectation_gap if previous.valuation else None
    current_gap = current.valuation.output.expectation_gap if current.valuation else None
    if previous_gap != current_gap:
        material.append("expectation_gap")
    if current_thesis == ThesisStatus.BROKEN and previous_thesis != ThesisStatus.BROKEN:
        material.append("thesis_broken")
    material.extend(item.flag.value for item in flag_changes if item.material)

    changes = (
        SnapshotChange(field="case", previous=previous.case.value, current=current.case.value),
        SnapshotChange(field="quant_grade", previous=previous.quant.grade.value if previous.quant.grade else None, current=current.quant.grade.value if current.quant.grade else None),
        SnapshotChange(field="current_trend", previous=previous.current_trend.overall.value if previous.current_trend else None, current=current.current_trend.overall.value if current.current_trend else None),
        SnapshotChange(field="narrative_gate", previous=previous.narrative_gate.value if previous.narrative_gate else None, current=current.narrative_gate.value if current.narrative_gate else None),
        SnapshotChange(field="thesis_status", previous=previous_thesis.value if previous_thesis else None, current=current_thesis.value if current_thesis else None),
        SnapshotChange(field="expectation_gap", previous=previous_gap.value if previous_gap else None, current=current_gap.value if current_gap else None),
        SnapshotChange(field="asymmetry_type", previous=previous.valuation.output.asymmetry_type.value if previous.valuation else None, current=current.valuation.output.asymmetry_type.value if current.valuation else None),
        SnapshotChange(field="valuation_confidence", previous=previous.valuation.output.confidence.value if previous.valuation else None, current=current.valuation.output.confidence.value if current.valuation else None),
        SnapshotChange(field="investment_grade", previous=grade_previous.value if grade_previous else None, current=grade_current.value if grade_current else None),
        SnapshotChange(field="thesis_breaker", previous=previous_breaker, current=current_breaker),
    )
    previous_kpi_version = previous.narrative.kpi_set_version if previous.narrative else 1
    current_kpi_version = current.narrative.kpi_set_version if current.narrative else 1
    previous_ids = previous.narrative.kpi_definition_ids if previous.narrative else ()
    current_ids = current.narrative.kpi_definition_ids if current.narrative else ()
    return SnapshotDiff(
        previous_snapshot_id=previous.snapshot_id,
        current_snapshot_id=current.snapshot_id,
        previous_kpi_set_version=previous_kpi_version,
        current_kpi_set_version=current_kpi_version,
        previous_kpi_definition_ids=previous_ids,
        current_kpi_definition_ids=current_ids,
        narrative_kpi_set_changed=previous_ids != current_ids,
        changes=changes,
        ticker=previous.ticker,
        previous_as_of=previous.as_of,
        current_as_of=current.as_of,
        metric_changes=metric_changes,
        signal_changes=signal_changes,
        narrative_changes=narrative_changes,
        flag_changes=flag_changes,
        valuation_change_type=valuation_change,
        grade_attribution=GradeChangeAttribution(previous_grade=grade_previous, current_grade=grade_current, reasons=frozenset(reasons)),
        material_changes=tuple(dict.fromkeys(material)),
    )
