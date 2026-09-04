# Case 2 Narrative v1 — Authoritative Specification

Status: FROZEN

Version: 1.0

Authoritative: YES

Last Updated: 2026-09-04

Implementation: `engine/narrative_engine.py`, `engine/case2_policy.py`

Tests: `tests/test_case2_calculation_engines.py`, `tests/test_case2_golden_validation.py`

Supersedes: `docs/narrative-v1.md` and earlier Narrative candidates

Change Policy: changes require an explicit design decision and version bump.

Narrative dimensions are Differentiation, Defensibility, Adoption,
Penetration / Expansion, Durability, and Failure Mode.

Allowed states are `PROVEN`, `STRONG`, `EMERGING`, `WEAK`, and `UNRESOLVED`.
Narrative is not converted into a numeric weighted score. TAM is context only and is
not a Quant or Narrative score.

## Narrative Gate

The Investment Grade gate is derived in priority order:

1. `BROKEN`: a predefined Thesis Breaker is triggered.
2. `WEAK`: Adoption is WEAK or core Narrative evidence is damaged.
3. `CONFIRMED`:
   - Adoption is STRONG or PROVEN;
   - Durability is STRONG or PROVEN;
   - Differentiation or Defensibility is STRONG or PROVEN;
   - no Thesis Breaker.
4. `QUALIFIED`:
   - Adoption is STRONG or PROVEN;
   - Durability is EMERGING, STRONG, or PROVEN;
   - Differentiation or Defensibility is STRONG or PROVEN;
   - no Thesis Breaker.
5. `DEVELOPING`: commercial evidence exists, the gate is not QUALIFIED, and no breaker exists.
6. `UNRESOLVED`: no commercial evidence exists from which to derive the gate.

CONFIRMED takes precedence over QUALIFIED. `UNRESOLVED` is an explicit schema state;
it is not a new investment rule and prevents missing evidence from becoming DEVELOPING.

## Versioning

Every Narrative snapshot stores Thesis Definition version, KPI-set version, and exact
KPI definition ids. A KPI set cannot change silently after results are released.
`SnapshotDiff` rejects changed KPI ids without a KPI-set version increment.
