# Investment Grade v1.1 — Decision Safety Specification

Status: FROZEN

Version: 1.1

Authoritative: YES

Last Updated: 2026-09-05

Implementation: `engine/investment_grade_engine_v1_1.py`, `engine/investment_grade_policy_v1_1.py`

Tests: `tests/test_decision_safety_v1_1.py`, `tests/test_case2_golden_validation.py`, `tests/test_persistence_phase1.py`

Supersedes: Investment Grade v1 for new decision snapshots only; `investment-grade-v1-frozen` remains authoritative for historical replay.

Change Policy: changes require an explicit design decision and version bump.

Investment Grade v1.1 is a judgment-safety revision. It changes no Case 1/2 Quant,
Current Trend, Narrative, Valuation, Funding Stress, or cap threshold. A frozen
calculation contract is reproducible policy, not evidence that the policy produces
superior investment returns.

## Version selection and immutable history

- Existing v1 snapshots and golden fixtures retain `investment-grade-v1-frozen`.
- New callers explicitly select v1.1 and store `investment-grade-v1.1-safety`.
- Re-evaluating identical evidence under v1.1 creates a new snapshot ID; it never
  overwrites a v1 result.
- Company grades are meaningful only with their fixture, `as_of`, information
  availability, valuation-assumption version, and Investment Grade policy version.

## Precedence

Apply in this order:

1. A valid predefined Thesis Breaker or Narrative `BROKEN` produces `X`.
2. Missing mandatory evidence produces `U` with a structured adjustment reason.
3. A resolved valuation produces an initial valuation grade under v1.1.
4. Existing frozen Case-specific gates and caps apply in their current order.

Terminal `X` therefore remains stronger than incomplete evidence. Upstream Quant,
Current, Narrative, and Valuation snapshots remain intact when final IG is `U`.

## Mandatory evidence

Case 1 requires:

- a resolved Quant grade with every Core metric resolved; and
- a resolved Valuation with resolved Expectation Gap and confidence.

Case 1 Narrative remains optional. Supporting-metric absence alone does not produce U.

Case 2 requires:

- an eligible resolved Quant grade with all frozen mandatory metrics resolved;
- a resolved mandatory Narrative Gate; and
- a resolved Valuation with resolved Expectation Gap and confidence.

The frozen shareholder-comparability exception remains valid: unresolved `dilution` and
`revenue_per_share_growth` may retain a resolved provisional Case 2 Quant result. Other
unresolved Core metrics do not satisfy the mandatory contract.

Current Trend remains optional. Missing or unresolved Current does not become neutral and
does not itself force `U`; it is recorded as `CURRENT_UNRESOLVED_OPTIONAL`.

Mandatory U reasons are:

- `MANDATORY_QUANT_UNRESOLVED`
- `MANDATORY_NARRATIVE_UNRESOLVED`
- `VALUATION_UNRESOLVED`
- `VALUATION_COMBINATION_UNRESOLVED`

## Confidence monotonicity

Lower valuation confidence cannot create a better initial grade when all economic
evidence is unchanged.

- POSITIVE + FAVORABLE starts at A; LOW confidence may only cap the final grade at B.
- OVERLAP, or POSITIVE + BALANCED, starts at B.
- NEGATIVE + UNFAVORABLE without compensating evidence starts at D regardless of HIGH,
  MEDIUM, or LOW confidence.
- NEGATIVE with explicitly supplied meaningful optionality or high stage sensitivity may
  start at C under the existing approved route.
- An otherwise unspecified NEGATIVE combination is U with
  `VALUATION_COMBINATION_UNRESOLVED`; LOW confidence is not optionality evidence.

The existing LOW-confidence maximum-B cap remains unchanged. A Funding Stress maximum-C
cap also remains active after price-only valuation changes.

## Case 2 Quant-only path

`Case2QuantBacktestAdapter` accepts the normalized frozen `Case2QuantInput` and calls
`build_case2_quant()` directly. It emits only the minimal historical-analysis shape and
Quant snapshot needed by the generic calibration contract. It requires no Narrative,
Current Trend, Valuation, market price/capitalization, or Investment Grade and invents no
neutral/default values for them.

The full Case 2 analysis adapter remains available and unchanged by default. For the same
Quant input, Quant-only and full-analysis outputs must match exactly. Future performance
remains a separate downstream record and can be unresolved when price data is absent.
