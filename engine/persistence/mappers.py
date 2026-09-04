"""Explicit domain ↔ ORM mapping functions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from engine.persistence.models import (
    AnalysisSnapshotRow,
    CompanyRow,
    CurrentTrendSignalRow,
    CurrentTrendSnapshotRow,
    ExitMultipleEvidenceRow,
    InstrumentRow,
    InvestmentGradeAdjustmentRow,
    InvestmentGradeSnapshotRow,
    MaterialEventRow,
    MetricResultRow,
    NarrativeAssessmentRow,
    NarrativeSnapshotRow,
    PriceSnapshotRow,
    QuantSnapshotRow,
    SourceReferenceRow,
    ThesisDefinitionRow,
    ThesisStatusSnapshotRow,
    TrackingKPIDefinitionRow,
    TrackingKPIObservationRow,
    ValuationAssumptionRow,
    ValuationSnapshotRow,
)
from engine.persistence.schemas import Company, Instrument, MaterialEvent, SourceReference
from engine.tracking_models import (
    AnalysisSnapshot,
    PriceSnapshot,
    ThesisDefinition,
    TrackingKPIDefinition,
    TrackingKPIObservation,
    ValuationAssumptionSet,
)


def _payload(model) -> dict:
    def json_value(value):
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("persistent datetime must be timezone-aware")
            return value.astimezone(timezone.utc).isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {key: json_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [json_value(item) for item in value]
        return value

    return json_value(model.model_dump(mode="python"))


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def company_to_row(company: Company) -> CompanyRow:
    values = company.model_dump()
    values["created_at"] = _utc(company.created_at)
    return CompanyRow(**values)


def company_from_row(row: CompanyRow) -> Company:
    values = {column.name: getattr(row, column.name) for column in CompanyRow.__table__.columns}
    values["created_at"] = _utc(values["created_at"])
    return Company.model_validate(values)


def instrument_to_row(instrument: Instrument) -> InstrumentRow:
    return InstrumentRow(**instrument.model_dump())


def instrument_from_row(row: InstrumentRow) -> Instrument:
    return Instrument.model_validate({column.name: getattr(row, column.name) for column in InstrumentRow.__table__.columns})


def source_to_row(source: SourceReference) -> SourceReferenceRow:
    values = source.model_dump()
    values["available_at"] = _utc(source.available_at)
    values["retrieved_at"] = _utc(source.retrieved_at)
    return SourceReferenceRow(**values)


def source_from_row(row: SourceReferenceRow) -> SourceReference:
    values = {column.name: getattr(row, column.name) for column in SourceReferenceRow.__table__.columns}
    values["available_at"] = _utc(values["available_at"])
    values["retrieved_at"] = _utc(values["retrieved_at"])
    return SourceReference.model_validate(values)


def price_to_row(price: PriceSnapshot, instrument_id: str) -> PriceSnapshotRow:
    return PriceSnapshotRow(
        price_snapshot_id=price.price_snapshot_id,
        instrument_id=instrument_id,
        timestamp=_utc(price.timestamp),
        price=price.price,
        currency=price.currency,
        market_cap=price.market_cap,
        enterprise_value=price.enterprise_value,
        source=price.source,
        price_type=price.price_type.value,
        analysis_snapshot_id=price.analysis_snapshot_id,
        created_at=_utc(price.created_at),
        payload=_payload(price),
    )


def price_from_row(row: PriceSnapshotRow) -> PriceSnapshot:
    return PriceSnapshot.model_validate(row.payload)


def valuation_assumption_to_row(
    assumption: ValuationAssumptionSet,
    *,
    company_id: str | None,
    instrument_id: str | None,
    valid_from: datetime,
    created_at: datetime,
) -> ValuationAssumptionRow:
    growth = assumption.plausible_growth_range
    return ValuationAssumptionRow(
        assumption_set_id=assumption.assumption_set_id,
        assumption_version=assumption.version,
        company_id=company_id,
        instrument_id=instrument_id,
        valid_from=_utc(valid_from),
        horizon_years=assumption.horizon_years,
        required_return=assumption.default_required_return,
        terminal_stage=assumption.terminal_stage.value,
        primary_metric=assumption.primary_metric.value,
        confidence=assumption.terminal_stage_confidence.value,
        plausible_growth_low=growth.low if growth else None,
        plausible_growth_high=growth.high if growth else None,
        expected_dilution=assumption.expected_annual_dilution,
        target_gross_margin=assumption.target_gross_margin,
        target_operating_margin=assumption.target_operating_margin,
        terminal_net_debt=assumption.terminal_net_debt,
        rationale=assumption.terminal_stage_rationale,
        created_at=_utc(created_at),
        payload=_payload(assumption),
    )


def exit_evidence_rows(
    assumption: ValuationAssumptionSet,
    valuation_assumption_id: int,
) -> list[ExitMultipleEvidenceRow]:
    return [
        ExitMultipleEvidenceRow(
            evidence_id=f"{assumption.assumption_set_id}:{assumption.version}:{item.band.value}",
            valuation_assumption_id=valuation_assumption_id,
            evidence_type=item.evidence_type.value,
            source_reference=item.source_reference,
            as_of=_utc(item.as_of),
            valuation_metric=item.metric_type.value,
            band=item.band.value,
            observed_low=item.value,
            observed_high=item.value,
            reference_value=item.value,
            rationale=item.rationale,
            payload=_payload(item),
        )
        for item in assumption.exit_multiples
    ]


def valuation_assumption_from_row(row: ValuationAssumptionRow) -> ValuationAssumptionSet:
    return ValuationAssumptionSet.model_validate(row.payload)


def thesis_to_row(
    thesis: ThesisDefinition,
    *,
    company_id: str | None,
    instrument_id: str | None,
    created_at: datetime,
    valid_to: datetime | None = None,
    why_now: str | None = None,
    why_this_company: str | None = None,
) -> ThesisDefinitionRow:
    return ThesisDefinitionRow(
        thesis_id=thesis.thesis_id,
        thesis_version=thesis.version,
        company_id=company_id,
        instrument_id=instrument_id,
        case=thesis.case.value,
        valid_from=_utc(thesis.effective_from),
        valid_to=_utc(valid_to),
        core_thesis=thesis.thesis,
        why_now=why_now,
        why_this_company=why_this_company,
        failure_modes=[thesis.failure_mode],
        kpi_set_version=thesis.kpi_set_version,
        created_at=_utc(created_at),
        payload=_payload(thesis),
    )


def thesis_from_row(row: ThesisDefinitionRow) -> ThesisDefinition:
    return ThesisDefinition.model_validate(row.payload)


def kpi_definition_to_row(
    definition: TrackingKPIDefinition,
    *,
    company_id: str | None,
    instrument_id: str | None,
    frequency: str | None = None,
) -> TrackingKPIDefinitionRow:
    return TrackingKPIDefinitionRow(
        kpi_definition_id=definition.kpi_definition_id,
        company_id=company_id,
        instrument_id=instrument_id,
        thesis_id=definition.thesis_id,
        thesis_version=definition.thesis_version,
        kpi_set_version=definition.kpi_set_version,
        kpi_key=definition.kpi_key,
        display_name=definition.name,
        primary_flag=definition.is_primary,
        direction=definition.direction.value,
        frequency=frequency,
        source_type=definition.source_requirement,
        breaker_rule=definition.breaker_condition,
        payload=_payload(definition),
    )


def kpi_definition_from_row(row: TrackingKPIDefinitionRow) -> TrackingKPIDefinition:
    return TrackingKPIDefinition.model_validate(row.payload)


def kpi_observation_to_row(
    observation: TrackingKPIObservation,
    *,
    company_id: str | None,
    instrument_id: str | None,
    created_at: datetime,
    analysis_snapshot_id: str | None = None,
    unit: str | None = None,
) -> TrackingKPIObservationRow:
    return TrackingKPIObservationRow(
        observation_id=observation.observation_id,
        kpi_definition_id=observation.kpi_definition_id,
        company_id=company_id,
        instrument_id=instrument_id,
        analysis_snapshot_id=analysis_snapshot_id,
        kpi_key=observation.kpi_key,
        thesis_version=observation.thesis_version,
        kpi_set_version=observation.kpi_set_version,
        period_end=observation.period_end,
        available_at=_utc(observation.available_at),
        as_of=_utc(observation.as_of),
        resolution_state=observation.state.value,
        value=observation.value,
        unit=unit,
        source_reference=observation.source_reference,
        created_at=_utc(created_at),
        payload=_payload(observation),
    )


def kpi_observation_from_row(row: TrackingKPIObservationRow) -> TrackingKPIObservation:
    return TrackingKPIObservation.model_validate(row.payload)


@dataclass(frozen=True)
class AnalysisRows:
    root: AnalysisSnapshotRow
    children: tuple[object, ...]


def analysis_to_rows(
    snapshot: AnalysisSnapshot,
    *,
    instrument_id: str,
    company_id: str,
    created_at: datetime,
    supersedes_snapshot_id: str | None = None,
    revision_reason: str | None = None,
) -> AnalysisRows:
    root = AnalysisSnapshotRow(
        snapshot_id=snapshot.snapshot_id,
        instrument_id=instrument_id,
        company_id=company_id,
        ticker=snapshot.ticker,
        period_end=snapshot.period_end,
        available_at=_utc(snapshot.available_at),
        as_of=_utc(snapshot.as_of),
        case=snapshot.case.value,
        case_version=snapshot.case_definition_version,
        analysis_version=snapshot.case_definition_version,
        price_reference_id=snapshot.reference_price_snapshot_id,
        supersedes_snapshot_id=supersedes_snapshot_id,
        revision_reason=revision_reason,
        created_at=_utc(created_at),
        payload=_payload(snapshot),
    )
    quant = snapshot.quant
    quant_row = QuantSnapshotRow(
        snapshot_id=quant.snapshot_id,
        analysis_snapshot_id=snapshot.snapshot_id,
        engine_version=quant.model_version,
        raw_score=quant.score,
        final_score=quant.score,
        raw_grade=quant.uncapped_grade.value if quant.uncapped_grade else None,
        final_grade=quant.grade.value if quant.grade else None,
        coverage=quant.coverage,
        provisional=quant.provisional,
        resolution_state=quant.state.value,
        payload=_payload(quant),
    )
    children: list[object] = [quant_row]
    children.extend(
        MetricResultRow(
            quant_snapshot_id=quant.snapshot_id,
            ordinal=index,
            metric_key=metric.name,
            raw_value=metric.value,
            normalized_value=metric.value,
            unit=metric.unit,
            grade=metric.grade.value if metric.grade else None,
            resolution_state=metric.state.value,
            source_period=quant.period_end,
            calculation_version=quant.model_version,
            normalization_notes=list(metric.supporting_tags) + ([metric.note] if metric.note else []),
            payload=_payload(metric),
        )
        for index, metric in enumerate(quant.metrics)
    )
    if snapshot.current_trend:
        current = snapshot.current_trend
        flags = {flag.value for flag in current.flags}
        children.append(CurrentTrendSnapshotRow(
            snapshot_id=current.snapshot_id,
            analysis_snapshot_id=snapshot.snapshot_id,
            overall_state=current.overall.value,
            engine_version=current.model_version,
            comparison_period=current.period_end,
            funding_stress="funding_stress" in flags,
            commercial_inflection="commercial_inflection" in flags,
            commercial_deterioration="commercial_deterioration" in flags,
            payload=_payload(current),
        ))
        children.extend(CurrentTrendSignalRow(
            current_trend_snapshot_id=current.snapshot_id,
            ordinal=index,
            signal_key=signal.name,
            state=signal.state.value,
            observation=signal.observation,
        ) for index, signal in enumerate(current.signals))
    if snapshot.narrative:
        narrative = snapshot.narrative
        children.append(NarrativeSnapshotRow(
            snapshot_id=narrative.snapshot_id,
            analysis_snapshot_id=snapshot.snapshot_id,
            narrative_version=narrative.model_version,
            thesis_id=narrative.thesis_id,
            thesis_version=narrative.thesis_version,
            kpi_set_version=narrative.kpi_set_version,
            overall_state=narrative.overall.value,
            narrative_gate=snapshot.narrative_gate.value if snapshot.narrative_gate else None,
            payload=_payload(narrative),
        ))
        children.extend(NarrativeAssessmentRow(
            narrative_snapshot_id=narrative.snapshot_id,
            ordinal=index,
            dimension=item.dimension,
            state=item.state.value,
            evidence=list(item.evidence),
            note=item.note,
        ) for index, item in enumerate(narrative.assessments))
    if snapshot.thesis_status:
        thesis_status = snapshot.thesis_status
        canonical_status = thesis_status.status
        children.append(ThesisStatusSnapshotRow(
            snapshot_id=thesis_status.snapshot_id,
            analysis_snapshot_id=snapshot.snapshot_id,
            thesis_id=thesis_status.thesis_id,
            thesis_version=thesis_status.thesis_version,
            kpi_set_version=thesis_status.kpi_set_version,
            status=canonical_status.value,
            breaker_triggered=thesis_status.breaker_triggered,
            observation_ids=list(thesis_status.observation_ids),
            payload=_payload(thesis_status),
        ))
    if snapshot.valuation:
        valuation = snapshot.valuation
        output = valuation.output
        assumption = valuation.assumption_set
        children.append(ValuationSnapshotRow(
            snapshot_id=valuation.snapshot_id,
            analysis_snapshot_id=snapshot.snapshot_id,
            assumption_set_id=assumption.assumption_set_id,
            assumption_version=assumption.version,
            required_return=assumption.default_required_return,
            horizon_years=assumption.horizon_years,
            terminal_stage=assumption.terminal_stage.value,
            expectation_gap=output.expectation_gap.value,
            bear_value=output.bear_value,
            base_value=output.base_value,
            bull_value=output.bull_value,
            downside_severity=output.downside_severity,
            upside_optionality=output.upside_optionality,
            asymmetry_type=output.asymmetry_type.value,
            valuation_confidence=output.confidence.value,
            market_price_reference=snapshot.reference_price_snapshot_id,
            payload=_payload(valuation),
        ))
    if snapshot.investment_grade:
        grade = snapshot.investment_grade
        children.append(InvestmentGradeSnapshotRow(
            snapshot_id=grade.snapshot_id,
            analysis_snapshot_id=snapshot.snapshot_id,
            initial_grade=grade.initial_valuation_grade.value,
            final_grade=grade.final_grade.value,
            engine_version=grade.model_version,
            payload=_payload(grade),
        ))
        children.extend(InvestmentGradeAdjustmentRow(
            investment_grade_snapshot_id=grade.snapshot_id,
            sequence=item.sequence,
            adjustment_type=item.adjustment_type.value,
            trigger=item.trigger.value,
            active=item.active,
            maximum_grade=item.maximum_grade.value if item.maximum_grade else None,
            reason=item.reason,
        ) for item in grade.adjustments)
    return AnalysisRows(root=root, children=tuple(children))


def analysis_from_row(row: AnalysisSnapshotRow) -> AnalysisSnapshot:
    return AnalysisSnapshot.model_validate(row.payload)


def material_event_to_row(item: MaterialEvent) -> MaterialEventRow:
    return MaterialEventRow(**item.model_dump())
