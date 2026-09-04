# Persistence Phase 1

Status: checkpointed v1

Persistence Phase 1 stores the existing frozen Case 1/Case 2 and Tracking Engine
outputs. It does not add, recompute, or reinterpret any investment rule.

## Boundary

```text
Pydantic domain model
        ↕ explicit mapper
SQLAlchemy ORM row
        ↕ explicit repository
SQLite locally / PostgreSQL later
```

Calculation modules do not import SQLAlchemy or database sessions. `SnapshotDiff`
remains an on-demand derived result; only optional material events have a table.

## Company and instrument identity

`Company` is the economic entity. `Instrument` is a tradable security belonging to a
company. A company may have multiple instruments. Ticker is display metadata, not a
global identifier; the database prevents duplicate `(exchange, ticker)` pairs while
allowing the same ticker on different exchanges. Every stored price references
`instrument_id`.

## Immutable analysis history

An analysis is an append-only root with normalized child rows for Quant metrics,
Current Trend signals, Narrative assessments, Thesis Status, Valuation, and Investment
Grade adjustments. The complete Pydantic payload is also retained to make the domain
round-trip lossless while the normalized columns remain queryable.

Repositories expose `add_analysis_snapshot`, `get_analysis_snapshot`,
`list_analysis_snapshots`, and `get_latest_analysis_snapshot`; there is no generic
update method. ORM hooks reject updates and deletes to historical rows.

A correction creates a new root and must supply both `supersedes_snapshot_id` and a
non-empty `revision_reason`. The superseded snapshot remains unchanged. Root and child
rows are flushed and committed in one transaction. Any child failure rolls back the
entire new analysis.

Unresolved domain values remain SQL `NULL` in metric columns and remain `unresolved` in
state columns. They are never converted to zero.

## Prices

Prices form an independent instrument time series and need not belong to an analysis.
`timestamp` and `created_at` must be timezone-aware at the domain boundary and are
normalized to UTC for relational ordering. A shared SQLAlchemy UTC type stores a naive
UTC value only on SQLite and restores it as aware `+00:00`; PostgreSQL uses native
timezone-aware timestamp semantics. The import key is
`(instrument_id, timestamp, source, price_type)`. Price must be positive; enterprise
value may be negative for a net-cash company.

## Thesis and KPI versions

Thesis definitions use `(thesis_id, thesis_version)` identity. KPI definitions use
`(kpi_definition_id, kpi_set_version)`. Observations must match a persisted KPI key,
thesis version, and KPI-set version. When linked to an analysis, an observation with
`available_at > analysis.as_of` is rejected.

Canonical thesis states are `CONFIRMING`, `NEUTRAL`, `WEAKENING`, `BROKEN`, and
`UNRESOLVED`. Legacy serialized `stable` input is normalized to `neutral` before
persistence, and a database check prevents new `stable` rows.

## Valuation assumptions and evidence

Valuation assumptions are immutable `(assumption_set_id, assumption_version)` records.
Price-only valuation snapshots keep the same version; changed business assumptions use
a new version. Historical valuation output is stored on each analysis and is not
recalculated when later assumptions change.

Each conservative/base/premium exit multiple has a normalized evidence row preserving
the evidence type, metric, source reference, as-of time, value/range fields, and
rationale. Supported evidence categories remain company history, comparable companies,
and business/capital-model evidence.

## Source provenance

`source_references` preserves source type, URI/reference, filing date, period end,
availability time, retrieval time, and notes. This phase stores provenance only; it does
not fetch SEC, DART, IR, or market data.

## Schema and migrations

- SQLAlchemy 2.x declarative schema
- Alembic static initial revision `20260904_0001`
- SQLite with foreign keys enabled for local development/tests
- PostgreSQL-compatible types and constraints; no running PostgreSQL dependency

The initial migration creates the schema from an empty database. Later migrations must
not invent missing values for legacy data.

## Known migration/compatibility concerns

- `engine.models.AnalysisSnapshot` is a legacy model distinct from the canonical
  tracking-domain snapshot.
- Historical `stable` thesis status needs explicit `stable → neutral` normalization.
- Old snapshots may lack `available_at`; no timestamp is inferred automatically.
- Old Case 2 serialization may use `loss_making_growth`; it must be explicitly mapped,
  not silently reclassified.
- Existing serialized objects may lack `instrument_id`; identity must be resolved before
  import.
- Original timezone labels/offsets are intentionally not retained. Persistence preserves
  the absolute instant and every DB-to-domain timestamp is restored as aware UTC.

## Explicit exclusions

No live feeds, filing fetchers, scheduler, REST API, dashboard, authentication, cloud
database, alerts, Performance Engine, technical indicators, Case 3+, or new investment
logic are included.
