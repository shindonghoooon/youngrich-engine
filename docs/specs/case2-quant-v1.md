# Case 2 Quant v1 — Authoritative Specification

Status: FROZEN

Version: 1.0

Authoritative: YES

Last Updated: 2026-09-04

Implementation: `engine/case2_policy.py`, `engine/case2_quant.py`

Tests: `tests/test_case2_calculation_engines.py`, `tests/test_case2_golden_validation.py`

Supersedes: `docs/case2-quant-v1.md` and earlier generic `loss_making_growth` proposals

Change Policy: changes require an explicit design decision and version bump.

Case 2 is `Emerging / Asymmetric Growth`. This document fixes the Quant policy;
company-specific exceptions are prohibited.

## Eligibility

Core Quant requires all of the following:

- core business revenue > 0;
- gross profit > 0;
- operating income < 0;
- core business revenue is representative;
- actual commercial customer/revenue evidence exists.

Pre-commercial companies are not scored. They may remain Edge/Watch with Quant
unresolved.

## Core 6

| Metric | Weight | Primary |
|---|---:|---|
| Revenue Growth | 30% | 2Y Revenue CAGR |
| Gross Profit Growth | 15% | 2Y Gross Profit CAGR |
| Cash Burn Trend | 15% | latest vs prior annual Case 2 FCF/burn |
| Runway | 15% | liquidity / latest annual cash burn |
| Dilution | 15% | fiscal period-end actual common shares |
| Revenue / Share Growth | 10% | annual revenue / period-end actual shares |

### Revenue Growth

```text
(latest revenue / revenue two years ago)^(1/2) - 1
```

| Grade | Threshold |
|---|---|
| A | >=40% |
| B | >=25% and <40% |
| C | >=15% and <25% |
| D | >=0% and <15% |
| X | <0% |

Store Growth Scope independently: `SAME_SCOPE`, `PRO_FORMA_COMPARABLE`,
`ACQUISITION_INFLUENCED`, or `UNRESOLVED`. Prefer official same-scope/organic,
then official pro-forma comparable, then reported acquisition-influenced growth.
Acquisition influence does not automatically reduce the grade.

### Gross Profit Growth

```text
(latest gross profit / gross profit two years ago)^(1/2) - 1
```

| Grade | Threshold |
|---|---|
| A | >=45% |
| B | >=30% and <45% |
| C | >=15% and <30% |
| D | >=0% and <15% |
| X | <0% |

Use the same Growth Scope normalization as Revenue Growth.

### Cash Burn Trend

Growth CAPEX includes PP&E purchases, capitalized internal-use software, and
capitalized product/software development. It excludes acquisition consideration,
securities purchases, and financial investments.

```text
Case 2 FCF = CFO - Growth CAPEX
Cash Burn = max(0, -FCF)
```

| Result | Grade |
|---|---|
| latest FCF >=0 | A |
| prior burn >0 and latest becomes FCF-positive | A |
| burn reduction >=30% | A |
| burn reduction >=10% and <30% | B |
| burn change within ±10% | C |
| burn increase >10% and <=50% | D |
| burn increase >50% | X |
| prior FCF >=0 and latest FCF <0 | X |

Rules are evaluated in the listed transition-first order. Thus exactly 10% burn
reduction is B and exactly 10% burn increase is C. Percentage comparison is unresolved
when its prior-burn denominator is zero; explicit FCF-positive-to-burning transitions
remain X.

### Runway

```text
Liquidity = cash + unrestricted short-term marketable securities
Runway months = Liquidity / latest annual cash burn × 12
```

Restricted cash is excluded.

| Result | Grade |
|---|---|
| FCF >=0 or runway >=36 months | A |
| >=24 and <36 months | B |
| >=12 and <24 months | C |
| >=6 and <12 months | D |
| <6 months | X |

### Dilution

Primary denominator is fiscal period-end actual common shares outstanding, not
weighted-average diluted shares.

| Actual share growth | Grade |
|---|---|
| <=2% | A |
| >2% and <=5% | B |
| >5% and <=10% | C |
| >10% and <=20% | D |
| >20% | X |

Include shares actually issued through ATM, follow-on offerings, SBC, M&A consideration,
and conversions. Unissued warrants/options/convertibles/preferred conversions/pre-funded
warrants are Potential Dilution supporting risk only. IPO/SPAC/direct-listing/reverse-
recapitalization comparisons that are not comparable are unresolved.

### Revenue / Share Growth

```text
Revenue per Share = Annual Revenue / Fiscal Year-End Actual Shares Outstanding
Growth = latest comparable annual / prior comparable annual - 1
```

| Growth | Grade |
|---|---|
| >=30% | A |
| >=20% and <30% | B |
| >=10% and <20% | C |
| >=0% and <10% | D |
| <0% | X |

An incomparable IPO/SPAC denominator is unresolved.

### Annual input comparability

Core 계산에 사용되는 연간 관측치는 연속된 회사 보고 FY label과 330–400일의 인접
`fiscal_period_end` 간격을 모두 충족해야 한다. 이는 52/53주 회계연도와 윤년을
허용하지만 결산기 변경 전환기간이나 임의 단기기간을 자동 연간화하지 않는다. 이 입력
계약 강화는 Core 6 가중치, threshold, formula를 변경하지 않는다.

## Score, missing-data policy, and guardrail

Grade points are A=4, B=3, C=2, D=1, X=0. Quant grades are A >=3.50,
B >=3.00, C >=2.40, D >=1.80, X <1.80.

Revenue Growth, Gross Profit Growth, Cash Burn Trend, and Runway are mandatory. If any
is unresolved, Quant is unresolved. If only Dilution and/or Revenue / Share Growth is
unresolved for comparability reasons, resolved weights are renormalized, the score is
marked provisional, and `coverage = resolved core weight / 100%` is stored. Unresolved
is never scored as zero.

If Cash Burn Grade=X and Dilution Grade=X, final Quant Grade is capped at D. Preserve
the raw score, uncapped grade, final grade, and active cap.

## Supporting only

- Gross Margin Trend
- Incremental Operating Margin
- Potential Dilution
- Growth Scope

Supporting metrics have zero weight. Incremental Operating Margin is
`ΔOperating Income / ΔRevenue`; when `ΔRevenue <=0`, store a scaling-failure signal
instead of a misleading positive ratio.
