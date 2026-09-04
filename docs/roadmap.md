# Milestone Roadmap

Status: ACTIVE

Authoritative for Milestone State: YES

Authoritative for Investment Rules: NO

Last Updated: 2026-09-04

Allowed milestone states are `COMPLETE`, `ACTIVE`, `PLANNED`, `BLOCKED`, and
`DEFERRED`. Frozen formulas live in [specifications](specs/), not in this roadmap.

## Current state

- Latest completed milestone: **M11 Historical Stress Calibration**
- Next research milestone: **M12 Systematic Historical Backtest — PLANNED**
- Parallel future product track: **M13–M15 — PLANNED**
- Case expansion: **M16 — DEFERRED**

No implementation milestone is currently `ACTIVE`; M12 must pass its decision gate
before implementation begins.

## M0 Project Framework

- Status: COMPLETE
- Goal: Establish Case-based analysis and separation of analytical layers.
- Deliverables: six-Case taxonomy, structured-data principle, no-look-ahead principle.
- Entry criteria: initial investment-engine concept.
- Exit criteria: project boundaries and source-of-truth model documented.
- Decisions required: none remaining for M0.
- Non-goals: production data ingestion and UI.

## M1 Case 1 Profitable Growth

- Status: COMPLETE / FROZEN v1
- Goal: Reproducible quality analysis for profitable growth companies.
- Deliverables: Core 8, fixed weights/thresholds, financial normalization, Cash
  Economics, standardized ROIC, Current Trend Overlay.
- Entry criteria: M0 complete and official financial fixtures available.
- Exit criteria: STRL end-to-end plus cross-company Annual/Current validation passes.
- Decisions required: none; reopen only through explicit versioned design decision.
- Non-goals: Capital Model benchmark calibration and company-specific formulas.

## M2 Case 2 Emerging / Asymmetric Growth

- Status: COMPLETE / FROZEN v1
- Goal: Retain real commercial adoption while identifying burn, runway, and dilution risk.
- Deliverables: six Core metrics, supporting signals, funding guardrail, Growth Scope,
  Narrative and Current Trend contracts.
- Entry criteria: Case 1 layering lessons established.
- Exit criteria: frozen policy implemented without company exceptions.
- Decisions required: none for v1.
- Non-goals: generic scoring of every loss-making company.

## M3 Common Valuation

- Status: COMPLETE / FROZEN v1
- Goal: Evaluate market-implied requirements separately from company quality.
- Deliverables: required-growth sensitivity, terminal stages, evidence-backed exit bands,
  Expectation Gap, scenarios, asymmetry, and confidence.
- Entry criteria: Case outputs defined.
- Exit criteria: deterministic Case 1/2 valuation calculations and tests pass.
- Decisions required: none for v1.
- Non-goals: price-driven mutation of assumption versions.

## M4 Investment Grade

- Status: COMPLETE / FROZEN v1
- Goal: Convert valuation result into a decision grade through explicit gates and caps.
- Deliverables: A/B/C/D/X/U, ordered adjustment trail, thesis-breaker representation.
- Entry criteria: Quant, Current, Narrative, and Valuation contracts available.
- Exit criteria: deterministic engine and regression tests pass.
- Decisions required: none for v1.
- Non-goals: weighted-average Investment Grade.

## M5 Tracking Domain Models

- Status: COMPLETE
- Goal: Define immutable, versioned cross-Case tracking records.
- Deliverables: Analysis, Quant, Current, Narrative, Thesis/KPI, Valuation, Investment
  Grade, Diff, Price, and Performance domain contracts.
- Entry criteria: frozen Case 1/2 layers.
- Exit criteria: temporal and unresolved invariants tested.
- Decisions required: future versions require explicit migration plans.
- Non-goals: full database or frontend.

## M6 Calculation Engines

- Status: COMPLETE
- Goal: Implement deterministic pure calculation paths for frozen Case 1/2 logic.
- Deliverables: orchestration and independent engine tests.
- Entry criteria: frozen specs and domain models.
- Exit criteria: full calculation regression passes.
- Decisions required: none for current version.
- Non-goals: fetching, persistence, and UI logic inside engines.

## M7 Case 2 Golden Validation

- Status: COMPLETE
- Goal: Compare production output against independent reference arithmetic.
- Deliverables: five offline real-world fixtures, discrepancy register, golden report.
- Entry criteria: M2–M6 complete.
- Exit criteria: production/reference agreement and corrected canonical outputs recorded.
- Decisions required: none.
- Non-goals: strategy backtest or threshold optimization.

## M8 Tracking / Thesis / Price Engine

- Status: COMPLETE
- Goal: Make prices, snapshot changes, thesis state, entry zones, and attribution auditable.
- Deliverables: immutable price snapshots, snapshot diff, versioned thesis/KPI evaluation,
  entry-zone calculation, grade-change attribution.
- Entry criteria: M5 complete.
- Exit criteria: point-in-time and immutability tests pass.
- Decisions required: provider choices deferred.
- Non-goals: live feeds and alerts.

## M9 Persistence

- Status: COMPLETE
- Goal: Persist canonical records without recalculating investment logic.
- Deliverables: append-only SQLAlchemy models, Alembic baseline, explicit mappers and
  repositories, SQLite/PostgreSQL compatibility checks.
- Entry criteria: stable domain contracts.
- Exit criteria: clean migration, no schema drift, round-trip and immutability tests pass.
- Decisions required: production database hosting remains open.
- Non-goals: provider ingestion and public API.

## M10 Performance Engine

- Status: COMPLETE
- Goal: Measure market outcomes downstream of immutable analysis.
- Deliverables: 1M/3M/6M/1Y horizons, return-since-analysis, MDD completeness, explicit
  benchmark assignments, comparable Alpha, cohort analytics and persistence.
- Entry criteria: exact reference PriceSnapshot and immutable AnalysisSnapshot.
- Exit criteria: adjusted-series, gap, horizon, Alpha, persistence, and cohort tests pass.
- Decisions required: production adjusted-price source remains open.
- Non-goals: portfolio execution, technical indicators, or feedback into historical grades.

## M11 Historical Stress Calibration

- Status: COMPLETE
- Goal: Validate analysis-to-performance plumbing on known winners and failures.
- Deliverables: 13 historical snapshots, 11 performance-resolved samples, offline prices,
  canonical grade cohorts, diagnostic report.
- Entry criteria: M10 checkpoint complete.
- Exit criteria: 320-test suite and `git diff --check` pass; limitations explicit.
- Decisions required: none; this result does not change frozen rules.
- Non-goals: unbiased strategy backtest, proven alpha, statistical significance, or
  threshold optimization.

See [Historical Stress Calibration v0.1](validation/historical-performance-stress-calibration-v0.1.md).

## M12 Systematic Historical Backtest

- Status: PLANNED / NEXT RESEARCH MILESTONE
- Goal: Evaluate the framework on a pre-defined point-in-time universe without selecting
  companies because they later won or failed.
- Deliverables: approved universe, deterministic snapshot cadence, point-in-time data
  model, delisted-security coverage, adjustment-safe history, historical router
  eligibility, versioned benchmarks, and cohort evaluation.
- Entry criteria: all five decision gates below approved.
- Exit criteria: frozen protocol, leakage tests, survivorship controls, reproducible
  offline dataset, and pre-declared analysis report.
- Decisions required: universe, cadence, providers, benchmark, date range, US-only versus
  US+KR.
- Non-goals: rule optimization on the evaluation sample.

### M12 implementation decision gate

Before full implementation, explicitly approve:

1. Universe v1
2. Snapshot Cadence v1
3. Data Source Plan v1
4. Benchmark Policy v1
5. Historical Date Range v1

No agent may silently invent these choices. See the
[research plan](research/systematic-backtest-plan.md).

## M13 EOD Data Layer

- Status: PLANNED
- Goal: Add reliable production EOD fundamentals/market-data inputs.
- Deliverables: provider adapter boundary, provenance, idempotent ingestion, corporate
  actions, retries, and data-quality monitoring.
- Entry criteria: provider and delayed/realtime requirements approved.
- Exit criteria: reproducible EOD snapshots and failure handling.
- Decisions required: production EOD provider and licensing.
- Non-goals: investment-rule changes.

## M14 API / Dashboard

- Status: PLANNED
- Goal: Expose stored canonical results without moving calculations into the view layer.
- Deliverables: read API, authentication decision, ranking/detail views, source and
  unresolved visibility.
- Entry criteria: M13 stable and API/dashboard technologies approved.
- Exit criteria: UI renders persisted snapshots faithfully.
- Decisions required: API and dashboard technology.
- Non-goals: dashboard-owned scoring.

## M15 PWA / Mobile / Alerts

- Status: PLANNED
- Goal: Add mobile access and event delivery after the data/API foundation is stable.
- Deliverables: PWA strategy, notification preferences, filing/grade/thesis alert policy.
- Entry criteria: M14 complete and product scope approved.
- Exit criteria: reliable delivery with audit trail and user controls.
- Decisions required: PWA timing, delayed versus realtime needs, alert channels.
- Non-goals: brokerage execution.

## M16 Cases 3–6

- Status: DEFERRED
- Goal: Expand Case coverage without weakening Case-specific economics.
- Deliverables: separately approved specs, fixtures, engines, and validation for each Case.
- Entry criteria: Case 1/2 productization stable and Case priority approved.
- Exit criteria: independent freeze criteria per Case.
- Decisions required: Case 3 versus Case 4 priority first.
- Non-goals: a universal scoring formula.

## Open Decisions

### Systematic Backtest — OPEN

- Initial stock universe
- US-only versus US+KR
- Minimum historical period and exact Historical Date Range v1
- Snapshot cadence
- Earnings-driven versus periodic analysis schedule
- Delisted-security source
- Point-in-time fundamental source
- Adjustment-safe historical price source
- Historical benchmark policy

### Product — OPEN

- Production EOD provider
- Delayed versus realtime price requirement
- API technology
- Dashboard technology
- PWA timing and alert scope

### Case Expansion — OPEN

- Case 3 versus Case 4 implementation priority

## Work-item mapping

Markdown owns architecture, frozen rules, roadmap state, decisions, validation, and
research boundaries. Future executable tasks may be mirrored into GitHub Issues and
grouped with GitHub Milestones. This file remains the design-level milestone source of
truth; no issue creation is implied or performed here.
