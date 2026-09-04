# ADR-0011: Generic Calibration Framework

Status: ACCEPTED

Date: 2026-09-04

## Context

Each investment Case needs different financial and qualitative logic, but duplicating
historical evaluation and research infrastructure per Case would increase complexity,
weaken comparability, and encourage outcome-driven rule changes. Requiring complete
historical Narrative and Valuation reconstruction for every broad-universe observation
would also block useful Quant and Current validation.

## Decision

All investment Cases use one common point-in-time snapshot → future outcome → calibration
protocol. Case-specific calculation enters through a `CaseBacktestAdapter`; the common
kernel only joins immutable canonical analysis/performance records and versioned research
metadata.

Broad systematic v1 does not require full historical Narrative. Missing Narrative is
first-class unresolved data, and deeper full-Investment-Grade evaluation may use a
pre-declared subset.

Research findings cannot mutate frozen policy. Any logic change requires repeated
validation, explicit design review, a new specification/engine version, and same-data
comparison while preserving the prior version.

## Why

- New Cases reuse performance, cohort, coverage, and finding infrastructure.
- Investment semantics remain owned by Case engines, not research plumbing.
- Point-in-time and unresolved contracts remain consistent.
- Layer coverage exposes the cost and incremental value of Current, Valuation, and
  Narrative.
- Version comparison measures changes without automatic threshold optimization.

## Alternatives considered

- A separate backtest engine for each Case.
- A generic kernel containing Case-specific conditionals.
- Requiring full historical Narrative/Valuation before any systematic test.
- Automatically optimizing thresholds from historical outcomes.

These alternatives were rejected because they duplicate infrastructure, leak Case
semantics into shared code, block broad deterministic testing, or increase overfitting
risk.

## Consequences

A future Case requires a policy/spec, calculation engine, and adapter, but no new common
calibration or performance engine. Market-specific SEC/DART/provider differences remain
outside the kernel. M12 systematic universe/data decisions remain a separate approval
gate under M12-B.

## Related documents

- [Generic Calibration Framework v1](../specs/calibration-framework-v1.md)
- [M12-B Systematic Data / Universe Plan](../research/systematic-backtest-plan.md)
- [Performance downstream-only](0010-performance-is-downstream-only.md)
