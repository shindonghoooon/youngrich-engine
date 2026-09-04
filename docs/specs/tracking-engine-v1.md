# Tracking Engine v1 — Phase 1

Status: FROZEN

Version: 1.0

Authoritative: YES

Last Updated: 2026-09-04

Implementation: `engine/price_tracking.py`, `engine/snapshot_diff.py`, `engine/thesis_engine.py`, `engine/entry_zone.py`

Tests: `tests/test_price_tracking_and_entry_zone.py`, `tests/test_snapshot_diff_engine.py`, `tests/test_thesis_engine.py`

Supersedes: `docs/tracking-engine-v1.md`

Change Policy: changes require an explicit design decision and version bump.

## Status and scope

Phase 1 implements pure, immutable tracking calculations on top of the frozen Case 1
and Case 2 engines. It adds no investment metric, threshold, technical indicator, data
provider, persistence, or alerting rule.

```text
Immutable AnalysisSnapshot[]
        +
Independent PriceSnapshot[]
        +
Versioned Thesis / KPI observations
        ↓
SnapshotDiff + ThesisStatus + EntryZone
```

Price is first-class investment data. Realtime pricing is not required for the current
engine. Price affects Valuation, Expectation Gap, Investment Grade, Entry Zone, and
future Performance Tracking. Technical momentum is outside v1.

## Immutable snapshots and price

An `AnalysisSnapshot` preserves the analysis-time `reference_price_snapshot_id`.
Subsequent prices are separate immutable `PriceSnapshot` records; they never overwrite
the old analysis or its assumptions.

`PriceSnapshot` stores ticker/company identity, timestamp, positive price, currency,
optional market cap and EV, source, price type, optional analysis reference, and
creation time. Phase 1 fixtures use CLOSE/EOD, but DELAYED and REALTIME are representable
without coupling the calculation engine to a provider.

`compare_prices()` requires the same ticker/currency and strictly later timestamp. It
returns absolute price change, return ratio, and market-cap/EV changes when both values
exist. It deliberately calculates no RSI, MACD, moving average, or momentum score.

Future progression:

- Phase 1: manual/EOD `PriceSnapshot`
- Phase 2: replaceable automated daily EOD provider
- Dashboard phase: delayed/realtime provider only if useful

The same series can later support return since analysis/tracking, 1M/3M/6M/1Y,
drawdown, benchmark-relative return and tracking-high calculations. Those Performance
Engine calculations are not implemented here.

## SnapshotDiff semantics

`build_snapshot_diff(previous, current)` requires the same ticker and a strictly later
`current.as_of`. It compares:

- Case and Case migration
- Quant grade and metrics by stable metric name/key
- Current overall state, individual signals, and flag transitions
- Narrative gate and each narrative dimension
- Thesis status and breaker state
- Expectation Gap, Asymmetry Type, Valuation Confidence
- Investment Grade

Metric, signal, and narrative changes use:

```text
IMPROVED / UNCHANGED / DETERIORATED
RESOLVED / BECAME_UNRESOLVED / NOT_COMPARABLE
```

Numeric direction alone does not imply economic direction. A graded metric follows its
grade transition, so dilution moving from 5% to 12% is deteriorated. An ungraded value
change is `NOT_COMPARABLE` unless semantic direction is separately defined.
`UNRESOLVED` is separate from unchanged and neutral.

Funding Stress, Commercial Inflection, and Commercial Deterioration flag transitions
are recorded independently. A false-to-true transition is material. Investment Grade,
Quant grade, Case, Expectation Gap and Narrative Gate changes are also always material;
a newly broken thesis is material.

## Thesis Tracking

`build_thesis_status()` evaluates versioned `TrackingKPIDefinition` and paired prior/current
`TrackingKPIObservation` records. Definition and observation ticker, thesis version,
KPI key, definition id, and KPI-set version must all match. A new KPI set creates a new
version; it does not rewrite historical observations or status snapshots.

Generic KPI direction is explicit:

- `HIGHER_IS_BETTER`
- `LOWER_IS_BETTER`
- `CUSTOM`
- `UNRESOLVED`

CUSTOM requires an explicit analyst-interpreted direction on the current observation.
There are no company-specific branches.

Aggregation is categorical and unweighted:

1. predefined breaker → `BROKEN`
2. fewer than two resolved primary KPIs → `UNRESOLVED`
3. deteriorating majority → `WEAKENING`
4. improving majority with no material narrative deterioration → `CONFIRMING`
5. otherwise → `NEUTRAL`

`STABLE` is accepted only as a legacy input and is immediately normalized to `NEUTRAL`.
New domain output, serialization, and persistence must never emit or store `STABLE`.
Unresolved KPI observations are excluded and never converted to neutral.

## Price-only valuation classification

Valuation changes are classified by immutable input identity:

- `PRICE_ONLY`: price/market cap changed and the complete assumption set did not
- `ASSUMPTION_CHANGE`: assumptions changed while price did not
- `MIXED`: both changed
- `NONE`: neither changed

The complete assumption object is compared, not just its version number, preventing an
unversioned assumption edit from being mislabeled as price-only. A price-only update may
change Expectation Gap and Investment Grade but cannot mutate the assumption set.

Grade-change attribution preserves every applicable reason:

```text
PRICE / QUANT / CURRENT_TREND / NARRATIVE / FUNDING
VALUATION_ASSUMPTION / THESIS_BREAKER / CASE_MIGRATION
DATA_RESOLUTION / MULTIPLE
```

`MULTIPLE` accompanies a grade change with more than one underlying reason; it does not
replace those reasons. A Case 2 → Case 1 transition is represented as material
`CASE_MIGRATION`; the engine does not route the company automatically.

## Entry Zone

Entry Zone is a valuation reverse calculation, not a technical support level and not a
new Investment Grade threshold.

For Case 1 PE:

```text
Future EPS = Current EPS × (1 + selected plausible EPS growth)^horizon
Maximum Price = Future EPS × Exit PE / (1 + required return)^horizon
```

For Case 2:

```text
Future Revenue = Current Revenue × (1 + selected plausible growth)^horizon
Future EV = Future Revenue × applicable terminal margin × exit multiple
Future Equity = Future EV - terminal net debt
Maximum Current Market Cap = Future Equity
  / [(1 + required return)^horizon × (1 + expected dilution)^horizon]
Entry Price = Maximum Current Market Cap / actual shares, when supplied
```

The applicable terminal margin is 1.0 for EV/Revenue, target gross margin for EV/GP,
and target operating margin for EV/EBIT. The result retains assumption-set identity and
version and produces conservative/base/premium bands rather than one magic price.

## Frozen-rule interaction

Price improvement does not bypass active caps. For example, an ONDS-like snapshot can
move from a NEGATIVE to OVERLAP Expectation Gap after a price decline while remaining
Investment Grade C because Funding Stress caps it at C. This is an expected frozen-rule
result, not a reason to change the cap.

## Explicit exclusions

No realtime API, SEC/DART ingestion, database, PostgreSQL, REST API, dashboard, PWA,
alerts, scheduler, technical indicator, Performance Engine, or Case 3+ logic is included.
