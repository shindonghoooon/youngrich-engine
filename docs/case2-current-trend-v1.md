# Case 2 Current Trend v1 — Authoritative Specification

Signals are Revenue Momentum, Gross Profit Momentum, Cash Burn Momentum,
Funding / Runway, and Thesis KPI Momentum. They never change Annual Quant.

## Revenue and Gross Profit Momentum

Use latest comparable YTD YoY; fall back to a comparable quarter only when YTD is not
possible. Apply the Annual Growth Scope rule.

| Growth | Signal |
|---|---|
| >=25% | POSITIVE |
| >=10% and <25% | NEUTRAL |
| <10% | NEGATIVE |

For Gross Profit, transition to negative GP is NEGATIVE plus a warning. Gross Margin
change is supporting only.

Revenue acceleration versus Annual Base is supporting only and is not counted in overall:

- current growth minus Annual Base >= +10%p: `ACCELERATING`
- current growth minus Annual Base <= -10%p: `DECELERATING`
- otherwise: `STABLE`

Exactly +10%p and -10%p are included in `ACCELERATING` and `DECELERATING` respectively.

## Cash Burn Momentum

```text
Current comparable YTD FCF = CFO - Growth CAPEX
```

- FCF >=0: POSITIVE
- burn reduction >=20%: POSITIVE
- burn change within ±20%: NEUTRAL
- burn increase >20%: NEGATIVE
- prior FCF-positive to current cash-burning: NEGATIVE
- prior cash-burning to current FCF-positive: POSITIVE

Transition rules are evaluated first. Exactly 20% burn reduction is POSITIVE and
exactly 20% burn increase is NEUTRAL.

## Funding / Runway

- runway >=24 months and actual share growth <=5%: POSITIVE
- runway >=12 months and actual share growth <=15%: NEUTRAL
- runway <12 months or actual share growth >15%: NEGATIVE
- required input not comparable: UNRESOLVED

## Thesis KPI Momentum

Use two to four primary KPIs from the company's versioned KPI set and evaluate in order:

1. Thesis Breaker triggered: `NEGATIVE`.
2. Fewer than two resolved primary KPIs: `UNRESOLVED`.
3. Improving count greater than deteriorating count: `POSITIVE`.
4. Deteriorating count greater than improving count: `NEGATIVE`.
5. Otherwise: `NEUTRAL`.

Unresolved KPIs are excluded rather than counted as neutral. KPI replacement requires a
KPI-set version increment.

## Flags

`FUNDING_STRESS` is active when current comparable cash-burn deterioration is >50%
and actual shares outstanding growth is >20%.

`COMMERCIAL_INFLECTION` is active when Annual Quant is D, X, or UNRESOLVED and Revenue,
GP, and Thesis KPI Momentum are all POSITIVE. It does not change Quant.

`COMMERCIAL_DETERIORATION` is active when Annual Quant is A or B and Revenue, GP, and
Thesis KPI Momentum are all NEGATIVE. It does not change Quant.

## Overall aggregation

Evaluate in this priority order:

1. fewer than four resolved signals: `UNRESOLVED`
2. positive >=4 and negative=0: `STRONG_POSITIVE`
3. positive >=2 and negative >=2: `MIXED`
4. positive >=3 and negative <=1: `POSITIVE`
5. negative >=3 and positive <=1: `NEGATIVE`
6. otherwise: `NEUTRAL`

`MIXED` must be evaluated before `POSITIVE`.
