# youngrich-engine

Status: ACTIVE PROJECT INDEX

Last Updated: 2026-09-06

## Mission

Build a versioned, point-in-time-safe stock analysis and tracking engine that separates
company quality, current business trend, valuation, and actual investment
attractiveness. The engine is designed to learn from immutable historical decisions and
their subsequent performance without leaking future information back into past analysis.

## Core Flow

```text
Stock
  → Case Router
  → Case Quant
  → Current Trend
  → Narrative where required
  → Valuation / Expectation Gap
  → Investment Grade
  → Immutable Tracking
  → Performance
  → Calibration
```

Structured source data and immutable snapshots are the source of truth. Reports and
future dashboards are views, never calculation authorities.

## Investment Philosophy

- Different economic structures require different Cases; there is no universal stock
  score.
- Quant measures business/financial quality. Investment Grade asks whether the stock is
  attractive at the current price.
- Current Trend and Narrative remain separate from Annual Quant.
- Valuation starts from market-implied required growth and an explicit Expectation Gap.
- Investment Grade uses ordered gates and caps, never a weighted average.
- `period_end`, `available_at`, and `as_of` remain separate to prevent look-ahead.
- Price is first-class data, but technical indicators are outside v1.
- Historical outcomes are downstream evidence and never rewrite old snapshots.

## Cases

| Case | Purpose | Status |
|---|---|---|
| 1. Profitable Growth | Profitable companies whose growth should compound per-share value | IMPLEMENTED / FROZEN v1 |
| 2. Emerging / Asymmetric Growth | Commercially adopting growth businesses whose economics are still emerging | IMPLEMENTED / FROZEN v1 |
| 3. Cyclical / Mean Reversion | Cycle-dependent earnings and balance-sheet recovery | RESEARCH / NOT IMPLEMENTED |
| 4. Quality Compounder | Long-duration quality where conventional growth routing is insufficient | RESEARCH / NOT IMPLEMENTED |
| 5. Large-cap Value / Mature Quality | Mature cash generation and valuation-led returns | RESEARCH / NOT IMPLEMENTED |
| 6. Asset / Special Situation | Asset value, restructuring, or event-driven asymmetry | RESEARCH / NOT IMPLEMENTED |

Case is the economic structure of the current investment idea, not a permanent company
label. Case 3–6 definitions are not implementation authorization.

## Current Milestone

**M11 Historical Stress Calibration: COMPLETE**

- 13 historical snapshots
- 11 performance-resolved
- intentionally curated and outcome-aware
- useful for engine and diagnostic validation only
- not an unbiased backtest and not evidence of proven alpha

**Current milestone: M12-B Case 1/2 Quant Systematic Test — ACTIVE DATA PILOT**

M12-A is COMPLETE / FROZEN and establishes a common, Case-agnostic calibration kernel
over immutable Analysis and Performance snapshots. The 2026-09-04 M12-B0
[free-data pilot](docs/validation/m12-b0-free-data-pilot-v0.1.md) returned a **FAIL entry
verdict** because no tested free source established historical security membership and
delisted continuity. The M12-B0.1
[Tiingo price follow-up](docs/research/tiingo-data-pilot-v0.1.md) is
**LIVE PRICE PILOT PASS WITH GAPS** and does not change that verdict. Full M12-B1
systematic execution cannot begin until that blocker,
Universe, US-versus-Korea scope, Snapshot Cadence, Historical Range, Fundamentals Source,
Market/Delisting Source, Benchmark Policy, and Narrative Mode v1 are explicitly
approved. The parallel future product track is:

```text
EOD Market Data → API → Dashboard → PWA / Alerts
```

No production provider or product technology has been selected. Tiingo is approved only
for the bounded research and limited operating pilot described above.

The parallel product track is now implementing a bounded
[STRL/TEM/LPTH operating connection](docs/limited-operating-flow.md) on branch
`feat/limited-operating-flow`. It is `DEMO/VALIDATION`, does not unblock M12-B1, and does
not authorize a production feed or UI. Its independent-audit response adds input and
comparison safety contracts without changing frozen weights, thresholds, or grades; see
the [audit validation record](docs/validation/limited-operating-independent-audit-2026-09-06.md).

## Frozen Components

These documents marked `FROZEN` are authoritative for production behavior:

- [Case 1 Profitable Growth v1](docs/specs/case1-v1.md)
- [Case 1 Current Trend v1](docs/specs/case1-current-trend-v1.md)
- [Case 2 Quant v1](docs/specs/case2-quant-v1.md)
- [Case 2 Current Trend v1](docs/specs/case2-current-trend-v1.md)
- [Narrative v1](docs/specs/narrative-v1.md)
- [Common Valuation v1](docs/specs/valuation-v1.md)
- [Investment Grade v1](docs/specs/investment-grade-v1.md)
- [Investment Grade v1.1 Decision Safety](docs/specs/investment-grade-v1.1.md) —
  default for explicitly selected new decision snapshots; v1 remains replayable
- [Tracking Schema v0.2](docs/specs/tracking-schema-v1.md)
- [Tracking Engine v1](docs/specs/tracking-engine-v1.md)
- [Persistence Phase 1](docs/specs/persistence-v1.md)
- [Performance Engine Phase 1](docs/specs/performance-engine-v1.md)

Case 1 supporting authoritative contracts:

- [Financial Input / Normalization v1](docs/specs/financial-input-v1.md)
- [Cash Economics v1](docs/specs/cash-economics-v1.md)
- [Capital Efficiency v1](docs/specs/capital-efficiency-v1.md)

Frozen specifications override research notes, validation interpretation, old reports,
and historical discussion. Changes require an explicit design decision and version bump.

## Implementation Status

| Layer | Status |
|---|---|
| Case 1 and Case 2 calculation engines | COMPLETE |
| Common Valuation and Investment Grade | COMPLETE / v1.1 SAFETY VERSIONED |
| Tracking domain, price, diff, thesis, and entry-zone engines | COMPLETE |
| Append-only persistence and Alembic schema | COMPLETE |
| Performance horizons, MDD coverage, benchmark alpha, and cohorts | COMPLETE |
| Generic Calibration Kernel M12-A | COMPLETE / FROZEN |
| M12-B0 free-first data pilot | COMPLETE WITH FAIL ENTRY VERDICT |
| M12-B0.1 Tiingo free-price pilot | COMPLETE / LIVE PRICE PATH PASS WITH GAPS |
| Systematic unbiased historical backtest | NOT IMPLEMENTED |
| Production EOD ingestion/API/dashboard/PWA | NOT IMPLEMENTED |
| Case 3–6 engines | NOT IMPLEMENTED |

## Validation Status

- [Case 2 Golden Validation](docs/validation/case2-golden-validation-2026-09-01.md): PASS
- [Investment Grade Decision Safety v1.1](docs/validation/decision-safety-v1.1.md): PASS
- [Tiingo Data Pilot v0.1](docs/validation/m12-b0.1-tiingo-data-pilot-v0.1.md): PASS WITH GAPS
- Calculation, Tracking, Persistence, and Performance regression: PASS
- Limited operating independent audit follow-up: LOCAL/REMOTE CI PASS / LIVE PENDING
- [Historical Stress Calibration v0.1](docs/validation/historical-performance-stress-calibration-v0.1.md): COMPLETE, outcome-aware only
- Systematic unbiased backtest: NOT YET COMPLETE

Historical Stress Calibration cannot establish unbiased expected return, proven alpha,
statistical significance, or optimal thresholds/weights.

## Current Canonical Corrections

Frozen code/spec output overrides earlier manual-memory estimates:

- IONQ Investment Grade = **C**
- ONDS Investment Grade = **C**
- EROC Current Trend = **NEUTRAL**

These are v1 validation-fixture correction records, not v1.1 outputs, current company
grades, recommendations, or new rules.

## Open Decisions

- Systematic historical universe and US-only versus US+KR scope
- Historical snapshot cadence and earnings-driven versus periodic schedule
- Point-in-time fundamental and delisted-security sources
- Historical adjusted-price provider and systematic benchmark policy
- Initial historical date range
- Production EOD provider and delayed versus realtime requirement
- API and dashboard technologies; PWA timing
- Case 3 versus Case 4 implementation priority after Case 1/2 productization

Detailed gates live in [the roadmap](docs/roadmap.md). Do not decide these implicitly
during implementation.

The common research architecture is documented in the
[Generic Calibration Framework](docs/specs/calibration-framework-v1.md). Its
governing rule is: every Case may use different investment logic, but every Case uses
the same historical validation protocol.

## Documentation Map

- [Developer handoff](docs/DEVELOPER_HANDOFF.md) — current checkpoint and next execution point
- [Limited operating flow](docs/limited-operating-flow.md) — STRL/TEM/LPTH DEMO/VALIDATION CLI
- [Roadmap](docs/roadmap.md) — milestone status, next work, and open decision gates
- [Architecture](docs/architecture.md) — stable system boundaries and data flow
- [Frozen specifications](docs/specs/) — authoritative rules and contracts
- [Decision records](docs/decisions/README.md) — why settled choices exist
- [Validation](docs/validation/) — observed test outcomes, not rule definitions
- [Research](docs/research/) — unapproved designs and future plans
- `reports/` — dated Case 1 validation evidence
- `engine/` and `tests/` — executable behavior and regression proof

Markdown owns architecture, rules, milestones, and decisions. Future executable work
items may be mirrored into GitHub Issues and grouped with GitHub Milestones, while
`docs/roadmap.md` remains the design-level milestone source of truth. This task does not
create GitHub issues.

## LLM Start Here

Read in this order:

1. `PROJECT.md`
2. `docs/roadmap.md`
3. `docs/architecture.md`
4. the relevant `docs/specs/*` files
5. the latest relevant `docs/validation/*` result
6. related `docs/decisions/*` records
7. implementation modules and their tests

**Frozen specifications override research notes and historical discussion.**

## LLM Operating Rules

1. Read `PROJECT.md` first and check `docs/roadmap.md` for the current milestone.
2. Treat `docs/specs/*` marked `FROZEN` as authoritative.
3. Do not implement a `RESEARCH` document without explicit approval.
4. Do not change frozen investment logic to make a known stock or result look better.
5. Validation results do not automatically change thresholds.
6. Preserve point-in-time and no-look-ahead discipline.
7. A company-specific issue cannot create a new common Quant metric without design approval.
8. Price changes may change Valuation/Investment Grade outputs but not valuation assumption versions.
9. Historical snapshots are immutable and new information creates a new snapshot.
10. Unresolved is a first-class state and never silently becomes zero, neutral, or false.

Tests remain the executable contract; these instructions are navigation and operating
context, not a substitute for regression coverage.
