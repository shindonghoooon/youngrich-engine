# Generic Backtest & Calibration Framework v1

Status: FROZEN

Version: 1.0

Authoritative: YES — Backtest/Calibration Architecture

Authoritative for Investment Logic: NO

Last Updated: 2026-09-04

Implementation: `engine/calibration_models.py`, `engine/calibration_engine.py`,
`engine/calibration_analytics.py`, `engine/case_backtest_adapters.py`

Tests: `tests/test_calibration_framework.py`, `tests/test_case2_golden_validation.py`

Supersedes: M12-A architecture sections previously held in
`docs/research/generic-calibration-framework-v1.md`

Change Policy: architecture changes require explicit design approval and a version bump.

## Governing principle

> Every Case may use different investment logic, but every Case must use the same
> historical validation protocol.

```text
Historical Point-in-Time Snapshot
  → Signal / Metrics
  → Future Outcome
  → Calibration Dataset
  → Research Finding
  → Human Review
  → New Logic Version
```

This flow never becomes `backtest result → automatic threshold update`. A proposed
change must proceed through a finding, hypothesis, repeated period/cohort validation,
explicit design decision or ADR, new specification/engine version, and a same-data
version comparison. Frozen historical snapshots remain unchanged.

## Scope

M12 is the broader **Generic Backtest & Calibration Framework**:

- **M12-A — Universal Calibration Kernel:** common records, adapters, research analytics,
  coverage, version comparison, and governance.
- **M12-B — Case 1/2 Quant Systematic Test:** point-in-time universe and data execution.
- **M12-C — Current Overlay Incremental Test:** same-cohort discrimination added by
  Current Trend.
- **M12-D — Valuation / Expectation Gap Incremental Test:** contemporaneous valuation
  evidence and coverage.
- **M12-E — Narrative / Full Investment Grade Subset Test:** deep, reproducible subset;
  broad historical Narrative is not required.
- **M12-F — Case Expansion / Router Validation:** only after enough Cases exist to make
  routing outcomes meaningful.

The existing [systematic plan](../research/systematic-backtest-plan.md) is retained as M12-B data and
universe research, not the definition of the common kernel.

## Kernel boundary

The common kernel knows only:

- immutable historical analysis and performance snapshot identities;
- Case and logic versions;
- generic metric results and signal/category outputs;
- future outcomes;
- provenance, data quality, cohorts, and research metadata.

It does not know what Revenue Growth, ROIC, Inventory Cycle, NAV, or Moat means. It does
not fetch market data, parse SEC/DART filings, calculate company financials, assign
Investment Grade, or optimize thresholds. A Case-specific `if/else` added to the common
kernel is an architecture failure.

Canonical data remains:

- `AnalysisSnapshot`
- `QuantSnapshot` and `MetricResult`
- `CurrentTrendSnapshot`
- `NarrativeSnapshot`
- `ValuationSnapshot`
- `InvestmentGradeSnapshot`
- `PerformanceSnapshot`

`CalibrationRecord` is a thin join over those immutable records. It does not copy Quant
metrics or performance returns.

## Domain contracts

### `CalibrationRun`

An immutable, reproducible research-run manifest records:

- run/calibration identity, Git commit, and creation time;
- universe/data versions and historical range;
- included Cases and per-Case logic version sets;
- Performance and optional Benchmark policy versions;
- run mode: `STRESS`, `SYSTEMATIC`, `PILOT`, `HOLDOUT`, or `WALK_FORWARD`;
- per-Case primary evaluation horizon;
- deterministic configuration hash;
- optional Development, Validation, and Holdout periods.

The configuration hash excludes runtime identity (`run_id`, creation time), Git commit,
and notes, but includes every research execution choice. The same configuration produces
the same hash; a logic-version change produces a different hash.

Primary horizon is configured per Case, not globally. Current v1 uses existing 1M, 3M,
6M, and 1Y `PerformanceSnapshot` outcomes. Adding 2Y/3Y later extends Performance data,
not Case adapters or the calibration kernel.

### `CalibrationRecord`

The record links one `AnalysisSnapshot` and one `PerformanceSnapshot` and stores only
research identity/version metadata:

- company and instrument identity;
- Case, Case version, Quant/Current/Valuation/Investment Grade versions;
- analysis `as_of` and calibration run;
- performance resolution state;
- `COMPLETE`, `PARTIAL`, or `UNRESOLVED` data quality;
- optional regime and cohort tags, boundary-sample marker, and source scope.

The kernel rejects mismatched analysis/performance IDs, ticker/instrument identities,
future evaluation before analysis, and versions incompatible with the run manifest.
Unresolved performance remains a visible joined record.

### `ResearchFinding`

A finding records component, type, description, evidence, sample count, qualitative
confidence, and status. Types include metric non-monotonicity, false-positive/negative
patterns, regime dependence, coverage issues, and valuation incremental effect. Status
moves through `OBSERVED`, `REQUIRES_VALIDATION`, `VALIDATED`, `REJECTED`, and
`CHANGE_CANDIDATE`.

A finding has no policy mutation method. Attempting direct mutation fails. Only a design
decision plus new spec/engine version may change investment logic.

## Case adapter protocol

`CaseBacktestAdapter` exposes:

```text
case
logic_version
is_eligible(input, as_of)
evaluate(input, as_of) → historical analysis-compatible output
```

Adapters receive already normalized, point-in-time inputs. Fetching and provider logic
stay in market-specific data adapters.

- Case 1 adapter calls the frozen `build_case1_snapshot` path and maps its legacy output
  into the canonical temporal tracking snapshot without recalculating formulas.
- Case 2 adapter calls the frozen `build_case2_analysis` orchestration directly.
- A test-only dummy cyclical adapter emits arbitrary `inventory_signal`/`cycle_signal`
  metrics and joins the kernel without changing common code. It is not Case 3 policy.

Future Case 3/4/5/6 delivery requires its own policy/spec, calculation engine, and
`CaseBacktestAdapter`. It must not require a new Performance engine, Calibration engine,
Cohort engine, or research-result storage architecture. This is an M12 acceptance
criterion.

## Metric research

`MetricResult` remains the source for raw calculated value, unit, resolution, and grade.
The research view may receive an optional normalized value without persisting or
overwriting the canonical metric. Historical data must never be reduced to final Quant
Grade alone.

Generic analytics group any `metric_key` by ordered grade and expose:

- N;
- mean and median forward return;
- positive-return rate;
- median MDD;
- median Alpha.

The ordered A/B/C/D/X table is the initial monotonicity diagnostic. v1 deliberately
does not force `MONOTONIC`/`PARTIAL` labels through arbitrary tolerances and never
optimizes thresholds.

## Incremental layers and coverage

The same historical snapshot cohort can be evaluated progressively:

1. Quant only;
2. Quant + Current;
3. Quant + Current + Valuation;
4. full Investment Grade / Narrative subset.

Every report states total records and resolved counts for Quant, Current, Valuation,
Narrative, and full Investment Grade. Comparing layers without showing differing sample
coverage is prohibited. Missing upper layers do not remove valid lower-layer records.

## False-positive and false-negative extraction

Research screens are explicit run inputs, never investment rules. Examples such as
`A/B and 1Y <= -30%` or `D/X and 1Y >= +100%` are configurable conditions. Extracted
candidates retain company, date, Case, canonical metrics/grades, Current direction,
Expectation Gap, and future outcome for failure analysis.

No default screen is permanent and no candidate automatically changes a policy.

## Same-data version comparison

Version comparison requires identical company, instrument, analysis timestamp, and
future outcome series. It reports metric/value/grade changes, Quant Grade changes, and
coverage changes for v1 versus v2. Both result sets coexist; the framework does not
select a winner automatically.

The governance loop is:

```text
CalibrationRun
  → ResearchFinding
  → repeat validation
  → ADR / design review
  → new spec and engine version
  → rerun the same immutable historical dataset
  → compare versions without rewriting v1
```

## Holdout and walk-forward discipline

Runs may store Development, Validation, and Holdout ranges. Exact dates are not frozen
yet. Once a period is declared holdout for one logic version, repeated threshold tuning
against it is prohibited.

Future `WALK_FORWARD` mode may design through year T and evaluate T+1, then roll forward.
This requires no machine-learning infrastructure and must preserve each run manifest.

Optional regime tags such as `LOW_RATE`, `RATE_HIKE`, `BULL`, or `BEAR` are research
metadata only. This document does not define a macro classifier and regime never enters
Investment Grade automatically.

## Router separation

Until Cases 1–6 exist, failure to qualify for Case 1 or Case 2 is not an investment
failure and not evidence that the Router is wrong. Current systematic evaluation is:

```text
Universe → Case 1 eligibility → Case 1 calibration
Universe → Case 2 eligibility → Case 2 calibration
```

Full Router accuracy belongs to M12-F. It cannot be inferred from uncovered Cases.

## Complexity budget

### Tier 1 — broad deterministic

Revenue, gross profit, operating income, CFO, CAPEX, cash, debt, shares, price, and market
cap. Suitable for the full systematic universe.

### Tier 2 — selectively scalable

Organic/same-scope revenue, backlog, NRR, and contemporaneous multiple evidence. These
have higher normalization and point-in-time evidence cost.

### Tier 3 — deep subset

Historical technology moat, management quality, competitive Narrative, and detailed
customer/adoption evidence. Broad systematic utility cannot depend on Tier 3 coverage.

## Market-agnostic data boundary

```text
US SEC / exchange / free-price adapters ─┐
                                        ├→ canonical snapshots → Calibration Kernel
KR DART / KRX / KR-price adapters ──────┘
```

The kernel never knows SEC versus DART. Korea ingestion is not part of M12-A. A future
Korea adapter must produce the same canonical identities, timestamps, data-quality
states, and snapshots.

M12-B follows a **free-first data pilot**: SEC/EDGAR fundamentals, free official
listing/universe evidence where possible, free multi-source historical prices, and
official corporate-action/delisting reconstruction. Norgate/CRSP remain paid fallback
and research references only if measured blockers remain.

## Persistence

No migration is added. The layer is a domain/research artifact over existing immutable
snapshots. Persistence should be considered only after M12-A/B usage proves stable query
and retention requirements.

## Explicit non-goals

- full universe download or SEC/DART crawler;
- paid/provider production client;
- threshold/weight optimizer, ML, or automatic winner selection;
- full historical Narrative reconstruction;
- production Cases 3–6 or full Router backtest;
- portfolio construction, dashboard, or alerting.

## Architecture acceptance

The minimal implementation demonstrates:

1. Case 1 and Case 2 use one calibration kernel.
2. A dummy Case 3-like adapter plugs in without common-kernel changes.
3. Raw metric values, optional normalized research values, and grades remain accessible.
4. Future outcomes remain generic and unresolved outcomes remain visible.
5. Layer-by-layer coverage is measurable.
6. Logic versions coexist and compare on identical outcomes.
7. Findings cannot mutate frozen logic.
8. Broad Quant testing does not require historical Narrative.
9. US/Korea provider differences stop at the data-adapter boundary.

Implementation: `engine/calibration_models.py`, `engine/calibration_engine.py`,
`engine/calibration_analytics.py`, `engine/case_backtest_adapters.py`

Tests: `tests/test_calibration_framework.py`,
`tests/test_case2_golden_validation.py`

Decision: [ADR-0011](../decisions/0011-generic-calibration-framework.md)
