# Common Valuation v1 — Authoritative Structural Specification

Status: FROZEN

Version: 1.0

Authoritative: YES

Last Updated: 2026-09-04

Implementation: `engine/valuation_engine.py`

Tests: `tests/test_valuation_investment_engines.py`, `tests/test_case2_golden_validation.py`

Supersedes: `docs/valuation-v1.md`, valuation v0.x candidates, and single fixed-exit-multiple proposals

Change Policy: changes require an explicit design decision and version bump.

Market prices are inputs. No current price is hard-coded and no real-time feed is part
of v1. Required-return sensitivities are 10%, 15% (default), and 20%.

## Versioned assumptions

Store horizon, required returns, terminal stage, terminal-stage rationale/confidence,
primary metric, plausible growth range, dilution, target margins, terminal net debt,
and exit multiple evidence in an immutable `ValuationAssumptionSet`.

A price-only update produces a new output with the same assumption id/version. It must
not expand a multiple or change a growth/margin/stage assumption because price changed.

## Case 1

Default horizon is three years. PE primary valuation uses:

```text
Required EPS CAGR =
[(Current Price × (1 + Required Return)^Horizon)
 / (Current EPS × Exit PE)]^(1/Horizon) - 1
```

EV/EBIT or FCF equivalents may be added only when configured as the primary metric;
PE cannot silently substitute. Plausible Growth Range is a versioned assumption.

For required range `[required_low, required_high]` and plausible range
`[plausible_low, plausible_high]`, Expectation Gap is:

- `POSITIVE`: `plausible_low > required_high`;
- `NEGATIVE`: `plausible_high < required_low`;
- `OVERLAP`: otherwise, including ranges that touch exactly at a boundary;
- `UNRESOLVED`: either range cannot be established from the required evidence.

No separate materiality threshold is introduced.

## Case 2

Default horizon is five years.

```text
Required Future Equity Value =
Current Market Cap
× (1 + Required Return)^Horizon
× (1 + Expected Annual Dilution)^Horizon

Required Future EV = Required Future Equity Value + Terminal Net Debt
```

For `GROWTH`:

```text
EV/Revenue: Required Revenue = Required EV / Exit EV-Revenue

EV/GP: Required GP = Required EV / Exit EV-GP
       Required Revenue = Required GP / Target Gross Margin
```

For `TRANSITION` or `MATURE`:

```text
Required EBIT = Required EV / Exit EV-EBIT
Required Revenue = Required EBIT / Target Operating Margin
```

Then:

```text
Required Revenue CAGR =
(Required Future Revenue / Current Revenue)^(1/Horizon) - 1
```

Metric/stage mismatches fail instead of silently substituting another multiple.

## Terminal stage and exit evidence

Terminal Stage is `GROWTH`, `TRANSITION`, or `MATURE`, with rationale and confidence.
It is not derived solely from revenue growth.

Every Conservative/Base/Premium multiple stores metric type, value, evidence type,
source, evidence as-of, and rationale. Evidence types are `COMPANY_HISTORY`,
`COMPARABLE_COMPANIES`, and `BUSINESS_CAPITAL_MODEL`.

## Confidence

Evaluate without a numeric score, in priority order:

1. no credible evidence: `UNRESOLVED`;
2. exactly one credible source, rapidly changing company economics, or LOW terminal-stage
   confidence: `LOW`;
3. at least two credible sources, stable company economics, and HIGH terminal-stage
   confidence: `HIGH`;
4. at least two credible sources: `MEDIUM`.
