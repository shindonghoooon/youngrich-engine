# Performance Engine Phase 1

Status: FROZEN

Version: 1.0

Authoritative: YES

Last Updated: 2026-09-04

Implementation: `engine/performance_engine.py`, `engine/performance_analytics.py`

Tests: `tests/test_performance_engine.py`, `tests/test_performance_analytics.py`, `tests/test_historical_performance_calibration.py`

Supersedes: `docs/performance-engine-v1.md`

Change Policy: changes require an explicit design decision and version bump.

Performance Engine v1 measures the market outcome after an immutable historical
analysis. It is downstream-only: realized prices never mutate or feed back into Quant,
Current Trend, Narrative, Valuation assumptions, or Investment Grade.

## Signal performance, not trade execution

The start price must be the exact `PriceSnapshot` referenced by the historical
`AnalysisSnapshot`. If that reference is missing or unavailable, performance is
`UNRESOLVED`; the engine never substitutes an arbitrary earlier close. The result is
analysis/signal performance, not a claim about an investor's executable or realized
portfolio return. A future Portfolio/Execution Engine would own that separate problem.

## Price basis and return type

Every price declares one basis:

- `RAW`: quoted price; rejected for Performance v1 because corporate actions can create
  false long-horizon returns.
- `SPLIT_ADJUSTED`: supports `PRICE_RETURN`.
- `TOTAL_RETURN_ADJUSTED`: supports `TOTAL_RETURN`.

Adjustment version and provider/reference metadata are retained. The engine does not
estimate dividends or repair an unsafe raw series. A synthetic two-for-one split
therefore remains unresolved with raw prices while a split-adjusted unchanged series
correctly returns zero.

## Calendar horizons

Standard horizons are 1M, 3M, 6M, and 1Y. Calendar-month arithmetic clips month-end
dates, so 2026-01-31 plus three months is 2026-04-30. For each target, the engine selects
the first eligible adjusted market price on or after the target date, within the
configured tolerance (seven calendar days by default). A future target or missing price
inside that window remains unresolved and is never stored as zero.

Return is calculated without early rounding:

```text
end price / start price - 1
```

Coverage is the resolved-horizon count divided by four. Later evaluations create new
PerformanceSnapshots as additional horizons mature; earlier evaluations are never
updated.

## Max drawdown and price-series completeness

MDD is calculated only from an adjustment-safe series (`SPLIT_ADJUSTED` or
`TOTAL_RETURN_ADJUSTED`). Every evaluation records a generic coverage result
(`SUFFICIENT`, `INSUFFICIENT`, or `UNRESOLVED`) plus observation count, first and last
timestamp, and maximum observed calendar-day gap.

The v1 coverage contract requires the exact analysis start price, at least two
observations, coverage beginning at that exact start and reaching the evaluation period
within the configured horizon tolerance, and no observed gap greater than
`mdd_max_gap_days` (seven calendar days by default). Only `SUFFICIENT` coverage permits:

```text
drawdown = price / running peak - 1
max drawdown = minimum observed drawdown
```

The convention is zero for no drawdown and negative for a loss from peak. Recovery does
not erase the historical trough. `RAW`, sparse, stale, or otherwise incomplete series
leave MDD unresolved rather than producing deceptive precision. The seven-day rule is
a market-data quality setting, not an investment threshold. An exchange-calendar-aware
coverage check may replace this calendar-day approximation later.

## Benchmark alpha

Benchmarks are explicit versioned `BenchmarkAssignment` records; the engine does not
hard-code SPY or infer a benchmark from country/sector. Benchmark calculations require
an exact configured benchmark start price. Stock and benchmark returns may each remain
resolved independently, but alpha additionally requires economically comparable series:
both must be `PRICE_RETURN` or both must be `TOTAL_RETURN`, and their effective start
and horizon-end dates must match exactly. For a comparable horizon:

```text
alpha = stock return - benchmark return
```

Missing benchmark data, return-type mismatch, start-date mismatch, and end-date mismatch
leave the stock return intact and alpha unresolved. A valid standalone benchmark return
is retained along with effective dates and a structured mismatch reason. The versioned
benchmark assignment is retained even when benchmark price coverage is incomplete.

## Persistence

`performance_snapshots` stores the immutable evaluation root and
`performance_horizons` stores one normalized row for each horizon. Both reference the
historical analysis, instrument, and exact price records. Repository operations are:

- `add_performance_snapshot`
- `list_performance_snapshots`
- `get_latest_performance_snapshot_for_analysis`

There is no update method. Benchmark assignments are also append-only and versioned.

## Cohort analytics

The pure cohort analyzer groups historical analysis context by:

- Case
- Investment Grade
- Quant Grade
- Expectation Gap
- Asymmetry Type
- Valuation Confidence
- Thesis Status
- Funding Stress
- Commercial Inflection

For a requested horizon it reports total snapshot count, resolved-return sample count,
mean/median/minimum/maximum return, positive-return rate, alpha sample count and
mean/median alpha, plus drawdown sample count and mean/median max drawdown. Unresolved
values are excluded only from the relevant denominator. Small samples remain visible
without claims of statistical significance.

When multiple evaluations exist for one historical analysis, cohort statistics use the
newest evaluation that resolves the requested horizon; if multiple evaluations resolve
it, the latest one wins. A newer unresolved update never erases an older resolved value,
and one investment judgment is not double-counted. The total number of supplied
evaluation snapshots remains visible separately. Research-only labels may be supplied
as an explicit mapping; absent Funding Stress or Commercial Inflection remains
`unresolved`, never silently `false`.

## Calibration boundary

Poor realized results do not automatically change model thresholds. Any future
calibration is a separate, versioned research process based on repeated evidence.

## Exclusions

No live/EOD provider, corporate-action processor, filing fetcher, execution engine,
broker integration, dashboard, alerts, scheduler, automatic calibration, technical
indicator, or Case 3+ logic is included.
