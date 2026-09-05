# ADR-0012: Investment Grade Decision Safety v1.1

Status: ACCEPTED

Date: 2026-09-05

## Context

Frozen Investment Grade v1 was reproducible, but executable reproduction exposed three
unsafe interpretation paths: unresolved Quant could skip its cap, Case 2 could continue
without a resolved mandatory Narrative Gate, and LOW valuation confidence could itself
create a C from a NEGATIVE valuation combination. Case 2 calibration also required the
full analysis input even when only frozen Quant was needed.

These are decision-evidence problems, not requests to optimize investment outcomes or
change frozen Case metrics.

## Decision

Preserve v1 unchanged for historical replay and add an explicitly selected v1.1:

1. predefined Thesis Breaker/Narrative BROKEN keeps first-priority X;
2. unresolved mandatory Case evidence returns U with a stable reason code;
3. valuation confidence may cap but never create a better initial grade;
4. unspecified valuation combinations return reasoned U rather than being guessed;
5. the existing Case caps, Funding Stress, and shareholder-comparability exception remain;
6. a separate Case 2 Quant-only adapter reuses `build_case2_quant()` without fake layers.

Every v1.1 evaluation uses a new immutable snapshot ID and records
`investment-grade-v1.1-safety`. Existing v1 fixtures are not rewritten.

## Consequences

Judgment is withheld when mandatory evidence is absent, and confidence deterioration is
monotonic with respect to grade. Some combinations previously receiving C only because
confidence was LOW now become U. This is an explicit safety correction, not performance
calibration. No database migration is required because engine version and reason already
exist in the persisted snapshot/adjustment contracts.

The B0 free-data verdict and Tiingo research status are independent and are not altered by
this ADR.
