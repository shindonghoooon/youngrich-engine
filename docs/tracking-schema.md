# Tracking Schema v0.1

## Status and scope

Tracking Schema v0.1 is the immutable, versioned domain contract for future tracking,
persistence, reporting, and dashboard work. It lives in `engine/tracking_models.py`.

It does not implement a database, dashboard, ingestion scheduler, price API, valuation
calculation, Case 2 scoring calculation, or Investment Grade calculation. It does not
change any frozen Case 1 rule.

## Snapshot time semantics

Every temporal snapshot keeps three separate fields:

- `period_end`: the economic or reporting period represented
- `available_at`: when the required information became public and usable
- `as_of`: the analysis information cutoff

Validation requires:

```text
period_end <= available_at.date()
available_at <= as_of
```

Historical prices use `ExecutablePriceSnapshot`. Its `executable_at` cannot precede
`information_available_at`, preventing later-released financial results from being
combined with an earlier year-end price.

## Primary models

| Model | Contract |
|---|---|
| `AnalysisSnapshot` | Immutable aggregate for one company, Case, and analysis date |
| `QuantSnapshot` | Versioned Case-specific metric results, score, grade, and caps |
| `MetricResult` | Resolved or unresolved metric; unresolved cannot contain zero/value |
| `CurrentTrendSnapshot` | Versioned current signals, overall direction, and flags |
| `NarrativeSnapshot` | Versioned narrative assessments tied to thesis/KPI versions |
| `ThesisDefinition` | Immutable version of a thesis and its KPI-set identity |
| `TrackingKPIDefinition` | Versioned KPI meaning and confirming/weakening/breaker rules |
| `TrackingKPIObservation` | Time-aware KPI observation with first-class unresolved state |
| `ThesisStatusSnapshot` | Historical confirming/stable/weakening/broken/unresolved result |
| `ValuationSnapshot` | Market price, versioned assumptions, and valuation output |
| `InvestmentGradeSnapshot` | Initial valuation grade plus explicit gates/caps |
| `SnapshotDiff` | Changes between immutable snapshots and KPI-version protection |
| `PerformanceSnapshot` | Returns/drawdown tied to an analysis and executable entry price |

Supporting contracts include `ValuationAssumptionSet`, `ExitMultipleAssumption`,
`ValuationOutput`, `NarrativeGate`, `InvestmentGradeAdjustment`, `GradeCap`, and
`ExecutablePriceSnapshot`.

## Immutability and versioning

All v0.1 models use Pydantic `frozen=True` and reject unknown fields. New financials,
prices, narrative evidence, or KPI observations create new snapshots. They never mutate
an older `AnalysisSnapshot`.

Explicit versions are required for:

- Case/Quant/Current/Narrative model definitions
- Thesis definitions
- Narrative KPI sets
- Valuation assumption sets
- Investment Grade model

`SnapshotDiff` rejects a changed narrative KPI id set unless `kpi_set_version` also
changes. This prevents a dashboard or tracking process from silently replacing the
evidence used to judge a thesis.

## Unresolved state

`ResolutionState.UNRESOLVED` is different from a numeric zero. An unresolved
`MetricResult` or `TrackingKPIObservation` must have `value=None`; providing `0` fails
validation. Resolved records must provide a value.

Quant snapshots may also be unresolved. An unresolved Quant snapshot cannot have a
score or grade.

## Case support

`AnalysisCase` explicitly supports:

- `case1_profitable_growth`
- `case2_emerging_asymmetric_growth`

The models use generic metrics, signals, assessments, flags, version ids, and evidence.
No company-specific fields are allowed.

Case 2 Quant snapshots can record the frozen `GrowthScope` values and the Cash Burn X +
Dilution X maximum-D `GradeCap`. Supporting metrics use `is_core=False` and zero weight,
so they do not change the frozen Core weights.

Case 2 Current Trend flags support Commercial Inflection, Funding Stress, and Commercial
Deterioration without adding another numeric metric.

## Valuation price-only updates

`ValuationAssumptionSet` stores the assumption identity and version. The default required
return is 15% within the 10% / 15% / 20% sensitivity set. Terminal stage, rationale,
confidence, plausible growth, dilution/margin inputs, and each evidence-backed
Conservative/Base/Premium exit multiple are versioned assumptions.

`ValuationSnapshot.reprice()` creates a new snapshot with a new price/output but carries
forward the same immutable assumption set. It does not accept an assumption replacement.
Changing an assumption requires a separately versioned assumption set and valuation snapshot.

## Investment Grade representation

Investment Grade uses `A/B/C/D/X/U`. `InvestmentGradeSnapshot` stores the valuation-derived
initial grade separately from the final grade. Each gate or cap records its trigger,
active state, maximum grade when relevant, and reason.

This schema deliberately contains no weighted-average Investment Grade function.

## Compatibility and migration

The current Case 1 pipeline imports `AnalysisSnapshot` and `MetricResult` from
`engine.models`. Tracking Schema v0.1 uses the same domain names in the separate
`engine.tracking_models` module to avoid breaking that frozen runtime.

There is no automatic conversion or database migration in v0.1. A future migration must:

1. map existing Case 1 snapshots into the versioned temporal fields;
2. derive `available_at` from stored source metadata rather than `period_end`;
3. preserve existing snapshot ids/history rather than overwrite records;
4. explicitly map the legacy `loss_making_growth` enum to Case 2 only after router and
   persistence compatibility are reviewed.
