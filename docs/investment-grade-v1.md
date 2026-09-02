# Investment Grade v1 — Authoritative Specification

Grades are `A`, `B`, `C`, `D`, `X`, and `U`. Investment Grade is never a weighted average.

## Initial valuation grade

- A candidate: Expectation Gap POSITIVE and Asymmetry FAVORABLE.
- B candidate: Expectation Gap OVERLAP, or POSITIVE with BALANCED asymmetry.
- C candidate: NEGATIVE with meaningful optionality, or highly stage-sensitive/low-confidence valuation.
- D candidate: NEGATIVE and UNFAVORABLE without a compensating watch reason.
- U: valuation unresolved.

Store the initial grade and its reason separately from the final grade. Combinations not
listed above are unresolved policy combinations and must not be guessed.

## Case 1 caps

- Quant A/B: no cap; C: max B; D: max C; X: max D.
- Current STRONG_POSITIVE/POSITIVE/NEUTRAL: no cap; MIXED: max B; NEGATIVE: max C.
- Commercial Deterioration: max D.
- Valuation Confidence HIGH/MEDIUM: no cap; LOW: max B; UNRESOLVED: U.
- Current unresolved: retain grade only if mandatory Quant/Valuation inputs exist,
  mark provisional/unresolved-current, and never treat it as neutral.

## Case 2 caps

- Narrative CONFIRMED: no cap; QUALIFIED: max B; DEVELOPING: max C;
  WEAK: max D; BROKEN: X.
- Quant A/B: no cap; C: max B; D: max C.
- Quant X with Commercial Inflection and Narrative >=QUALIFIED: max C;
  otherwise max D.
- Current STRONG_POSITIVE/POSITIVE/NEUTRAL: no cap; MIXED: max B; NEGATIVE: max C.
- Commercial Deterioration: max D.
- Funding Stress: max C.
- Valuation Confidence HIGH/MEDIUM: no cap; LOW: max B; UNRESOLVED: U.
- Thesis Breaker or Narrative BROKEN: X.

## Global precedence and reproducible ordering

Evaluate global terminal states first:

1. Thesis Breaker active or Narrative Gate `BROKEN`: final grade `X`.
2. Valuation unresolved: final grade `U`.
3. Otherwise derive the initial valuation grade and apply normal Case-specific caps in
   recorded order.

Therefore Valuation `U` combined with a Thesis Breaker or BROKEN Narrative resolves to
final grade `X`.

Every active gate/cap stores a unique sequence number, trigger, maximum grade where
applicable, and reason. The engine applies stored adjustments in sequence and retains
every trigger, so the final result is reproducible. Ordinary caps select the most
restrictive grade reached; Thesis Breaker forces X.

