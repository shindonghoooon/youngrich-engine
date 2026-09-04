# Architecture

Status: ACTIVE

Authoritative for Boundaries: YES

Authoritative for Investment Rules: NO — see `docs/specs/`

Last Updated: 2026-09-04

## System flow

```text
External / Curated Data
          ↓
Normalization + provenance
          ↓
Case Router
          ↓
Case Quant
          ↓
Current Trend + Narrative where required
          ↓
Valuation / Expectation Gap
          ↓
Investment Grade gates and caps
          ↓
Immutable AnalysisSnapshot
          ↓
Append-oriented Persistence
          ↓
Tracking / Diff / Thesis
          ↓
Downstream Performance
          ↓
Calibration / future Dashboard views
```

Frozen formulas and thresholds live only in [specifications](specs/). This document
defines component ownership and allowed data direction.

## Price as first-class data

```text
PriceSnapshot
  ├─→ Valuation → Expectation Gap → Investment Grade
  ├─→ Entry Zone
  └─→ Performance horizons / MDD / benchmark Alpha
```

Price-only changes may recalculate valuation output but never mutate the associated
valuation assumption version. Technical indicators are outside v1.

## Boundaries

### Source and normalization

- External or manually curated data carries source, period, availability, and retrieval
  metadata.
- `period_end`, `available_at`, and `as_of` are distinct.
- Data with `available_at > as_of` is rejected.
- Normalization produces comparable domain inputs; it does not assign investment grades.

### Calculation engines

- Pure and deterministic.
- No database access, network fetching, UI state, or company-specific hidden overrides.
- Case Quant, Current Trend, Narrative, Valuation, and Investment Grade remain separate
  calculations.
- Unresolved is preserved and never coerced to zero, neutral, or false.

### Case Router

- Runs before Case Quant.
- Routes the economic structure of the current investment idea.
- Cases 1 and 2 are implemented; Cases 3–6 remain research.
- Ambiguous boundaries stay unresolved rather than expanding router rules ad hoc.

### AnalysisSnapshot

- Captures the exact point-in-time analytical state.
- References the exact executable/reference `PriceSnapshot` where available.
- Is immutable; corrected or updated analysis appends a new version.
- Future market outcomes cannot enter this object.

### Persistence

- SQLAlchemy/Alembic schema is append-oriented and version-aware.
- Repositories persist domain outputs but do not calculate investment logic.
- Company is the durable business identity; Instrument represents a tradable listing.
- Ticker alone is not a global identity.

### Tracking

- Compares immutable snapshots and evaluates versioned thesis KPIs.
- Narrative/Thesis KPI sets cannot silently change between periods.
- Price, thesis status, and grade-change attribution remain auditable.

### Performance

- Strictly downstream of historical analysis.
- Uses adjustment-safe price series and explicit benchmark assignments.
- Alpha requires matching return type and effective start/end dates.
- MDD requires sufficient series coverage.
- A performance result never mutates Quant, Narrative, Valuation assumptions, or
  Investment Grade.

### Calibration and research

- Validation observes behavior under frozen rules; it does not redefine them.
- Historical Stress Calibration is curated/outcome-aware and diagnostic only.
- A future Systematic Historical Backtest requires a pre-approved point-in-time
  universe, schedule, data plan, date range, and benchmark policy.

### Dashboard and API

- Future view/access layers only.
- Never source of truth and never owners of financial or investment calculations.
- Technology and provider choices remain open.

## Runtime dependency direction

```text
data/schema models
      ↑
pure engines
      ↑
orchestration
      ↑
persistence repositories
      ↑
future API / dashboard
```

Research-time networked curators may create reviewed offline fixtures. Production engines
and pytest remain network-free.

## Related documents

- [Project index](../PROJECT.md)
- [Roadmap](roadmap.md)
- [Frozen specifications](specs/)
- [Architecture decisions](decisions/README.md)
- [Validation evidence](validation/)
- [Research plans](research/)
