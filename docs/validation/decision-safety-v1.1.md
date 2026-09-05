# Investment Grade Decision Safety v1.1 Validation

Status: VALIDATION — PASS

Authoritative for Results: YES

Authoritative for Investment Rules: NO

Last Updated: 2026-09-05

## Scope

This validation reproduces the identified v1 judgment paths and verifies the separately
versioned v1.1 behavior. It does not change Quant, Current Trend, Narrative, Valuation,
Funding Stress, Case eligibility, or future-performance formulas.

## Reproduction and correction

| Scenario | v1 observed behavior | v1.1 behavior |
|---|---|---|
| Case 1 mandatory Quant unresolved + favorable Valuation | A because Quant cap was skipped | U — `MANDATORY_QUANT_UNRESOLVED` |
| Case 2 Narrative missing/unresolved + otherwise favorable inputs | Evaluation continued | U — `MANDATORY_NARRATIVE_UNRESOLVED` |
| NEGATIVE + BINARY, no C evidence, HIGH confidence | unspecified exception | U — `VALUATION_COMBINATION_UNRESOLVED` |
| Same NEGATIVE + BINARY inputs, LOW confidence | C from confidence alone | U — same structured reason |
| NEGATIVE + UNFAVORABLE, no C evidence | D | D at HIGH and LOW confidence |
| POSITIVE + FAVORABLE | A | A at HIGH; LOW only caps to B |
| Valid Breaker with missing mandatory inputs | X | X remains first priority |

The Case 2 shareholder-comparability provisional path remains usable. Case 1 Narrative
absence and optional Current absence do not force U; unresolved Current is retained as an
explicit observation rather than converted to neutral.

## Quant-only and persistence

The Case 2 Quant-only adapter produces the exact same Quant snapshot as the full Case 2
analysis for the TEM golden input while leaving Current, Valuation, and Investment Grade
absent. The v1.1 model version and structured safety reason survive domain-to-SQL-to-domain
round-trip without a migration.

The existing Case 2 golden v1 result set remains unchanged. Full-suite and documentation
test totals are reported in the execution handoff rather than treated as investment-rule
evidence.

## Versioned Case 2 comparison

The same five golden inputs were replayed with new snapshot IDs and explicit v1.1
selection. Quant outputs were identical in every pair.

| Fixture | v1 final | v1.1 final | v1.1 interpretation |
|---|---|---|---|
| TEM | B | B | unchanged |
| IONQ | C | D | LOW confidence no longer creates the C entry route |
| ONDS | C | D | LOW confidence no longer creates the C entry route |
| LPTH | C | U | negative combination lacks explicit C evidence |
| EROC | U | U | mandatory Quant remains unresolved, now with explicit reason |

These are versioned policy outputs, not retroactive corrections to the v1 golden record.
