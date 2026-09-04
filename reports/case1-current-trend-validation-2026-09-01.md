# Case 1 Current Trend Overlay v1 Validation — 2026-09-01

Status: VALIDATION

Authoritative for Results: YES

Authoritative for Investment Rules: NO — see [Case 1 Current Trend v1](../docs/specs/case1-current-trend-v1.md)

## Decision

**FROZEN**

The existing Current Trend Overlay v1 rules ran without company-specific exceptions
for four companies. Oracle is legitimately unresolved because no official post-FY2026
comparable period existed as of 2026-09-01. This is a successful look-ahead prevention
result, not missing-data remediation work.

The two repeated cross-company issues were minimally calibrated without changing the
Annual engine or adding a Current metric. The official fixtures now complete the
five-company regression without a new common distortion.

## Cross-company result

| Ticker | Annual Quant | Current Revenue | Current Op Profit | Current Margin | Current Cash | Current Balance | Overall |
|---|---:|---|---|---|---|---|---|
| STRL | 3.65 / A | positive | positive | positive | neutral | neutral | positive |
| ORCL | 2.70 / C | unresolved | unresolved | unresolved | unresolved | unresolved | unresolved |
| 003230.KS | 4.00 / A | neutral | negative | neutral | negative | neutral | neutral |
| LLY | 3.80 / A | positive | positive | positive | positive | neutral | positive |
| 010120.KS | 3.15 / B | positive | positive | positive | negative | neutral | positive |

The Annual Quant scores and grades are unchanged. Current Trend is an overlay and did
not modify the Annual Base metrics, weights, score, or grade.

## Official sources and periods

| Ticker | Current comparison | Primary official source | Filing date |
|---|---|---|---|
| STRL | H1 2026 vs H1 2025 | [SEC 2026 Q2 10-Q](https://www.sec.gov/Archives/edgar/data/874238/000087423826000103/strl-20260630.htm) and [official earnings release](https://www.sec.gov/Archives/edgar/data/874238/000087423826000100/a20260803ex991earningsrele.htm) | 2026-08-04 / 2026-08-03 |
| ORCL | No eligible period | [SEC submissions history](https://data.sec.gov/submissions/CIK0001341439.json) and [FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm) | latest annual filing 2026-06-22 |
| 003230.KS | H1 2026 vs H1 2025 | [DART half-year report](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260814003053) | 2026-08-14 |
| LLY | H1 2026 vs H1 2025 | [SEC 2026 Q2 10-Q](https://www.sec.gov/Archives/edgar/data/59478/000005947826000081/lly-20260630.htm) | 2026-08-05 |
| 010120.KS | H1 2026 vs H1 2025 | [DART half-year report](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260814003088) | 2026-08-14 |

All fixture sources and period ends precede or equal `as_of=2026-09-01`. No estimate,
consensus figure, unofficial financial site, or future filing is used.

## Reproduced observations

### STRL regression

- Revenue growth: 90.72% vs 12.06% Annual Base CAGR — positive.
- Operating profit growth: 122.28% vs 36.42% — positive.
- Margin change: +2.5427pp — positive.
- CFO conversion: 1.2041x vs 1.9567x — neutral because absolute conversion remains healthy.
- Net debt / TTM EBITDA: -0.2664x vs -0.2073x — neutral.
- Counts: 3 positive, 0 negative, 2 neutral; overall is positive.
- Annual Quant remains 3.65 / A.

### Oracle

Oracle's Annual Base already includes FY2026 through 2026-05-31. The SEC submissions
available by 2026-09-01 contain the FY2026 10-K but no FY2027 Q1 10-Q or official
post-FY2026 comparable result. Therefore all Current sub-signals and the overall signal
are unresolved.

FY2026 Annual data was not reused as a Current period, and no FY2027 estimate or
look-ahead value was introduced. Annual Quant remains 2.70 / C.

### Samyang Foods

- Revenue growth: 37.21% vs 37.28% Annual Base CAGR — neutral.
- Operating profit growth: 39.06% vs 79.67% — negative.
- Margin change: +0.3166pp — neutral.
- CFO conversion: 0.9511x vs 1.0620x; current/base = 89.56% — negative.
- CAPEX / CFO: 0.3852x, supporting observation only.
- Net debt / TTM EBITDA: -0.0411x vs 0.1810x — neutral.
- Overall: neutral. Annual Quant remains 4.00 / A.

TTM EBITDA is KRW 700.312bn, reproduced as FY2025 EBITDA KRW 587.938bn plus
H1 2026 EBITDA KRW 394.097bn minus H1 2025 EBITDA KRW 281.723bn. H1 EBITDA uses
reported operating income plus depreciation and amortization disclosed in the DART
cash-flow note. Current debt includes short-term borrowings, current long-term
liabilities, and long-term borrowings.

### Eli Lilly

- Revenue growth: 51.22% vs 31.69% Annual Base CAGR — positive.
- Operating profit growth: 69.41% vs 54.53% — positive.
- Margin change: +4.4924pp — positive.
- CFO conversion: 1.1057x vs 0.8190x — positive.
- CAPEX / CFO: 0.3282x, supporting observation only.
- Net debt / TTM EBITDA: 1.2862x vs 1.2451x — neutral.
- Overall: positive. Annual Quant remains 3.80 / A.

Reported GAAP operating income is reproduced from the 10-Q income statement: revenue
less cost of sales, R&D, marketing/selling/administrative, acquired IPR&D, and asset
impairment/restructuring/special charges. It is USD 17.893bn for H1 2026 and
USD 10.562bn for H1 2025. No adjusted or non-GAAP operating figure is used.

TTM EBITDA is USD 35.732bn, reproduced as FY2025 EBITDA USD 28.299bn plus H1 2026
EBITDA USD 18.936bn minus H1 2025 EBITDA USD 11.503bn.

### LS ELECTRIC

- Revenue growth: 32.74% vs 13.71% Annual Base CAGR — positive.
- Operating profit growth: 55.73% vs 31.50% — positive.
- Margin change: +1.5252pp — positive.
- CFO conversion: -0.3492x vs 1.0144x — negative.
- CAPEX / CFO: unresolved because current cumulative CFO is negative; it does not alter the grade.
- Net debt / TTM EBITDA: 1.1910x vs 1.0375x — neutral.
- Counts: 3 positive, 1 negative, 1 neutral; overall is positive under the majority rule.
- Annual Quant remains 3.15 / B.

TTM EBITDA is KRW 676.334bn, reproduced as FY2025 EBITDA KRW 558.723bn plus
H1 2026 EBITDA KRW 377.104bn minus H1 2025 EBITDA KRW 259.494bn. Every bridge
component is based on official reported operating income and depreciation/amortization;
no quarter or half-year annualization is used.

## Special analysis

### A. Absolute-good / relative-negative

The absolute-health calibration resolves the repeated distortion:

- STRL: current CFO conversion is 1.2041x, so relative deterioration is recorded but
  the signal is neutral under the reused Annual A-grade threshold.
- Samyang Foods: current CFO conversion is 0.9511x, below the 1.00x health threshold,
  so its true relative deterioration remains negative.

The 1.00x floor is not a new threshold: it reuses the existing Annual Cash Economics
A-grade boundary. CAPEX/CFO remains a supporting observation and does not alter the signal.

### B. Overall signal dilution

The majority calibration resolves both observed cases:

- STRL: after cash calibration, 3 positive and 2 neutral becomes overall positive.
- LS ELECTRIC: 3 positive, 1 negative, 1 neutral becomes overall positive.

The overall layer remains unscored and does not change Annual Quant.

## Freeze assessment and unresolved items

The result is **Current Trend Overlay v1 = FROZEN**:

- Four companies calculate through the same model and comparable-period rules.
- ORCL's unresolved result demonstrates correct look-ahead prevention and does not
  prevent a future Freeze decision by itself.
- The absolute-good cash distortion and majority-signal dilution are resolved.
- No new common distortion appeared in the five-company rerun.
- No Annual Core, Annual rule, Current metric, score, or company exception was changed.

Unresolved follow-up items:

1. Re-run ORCL only after an official post-FY2026 comparable period is published.
2. LS ELECTRIC's negative H1 CFO makes CAPEX/CFO mathematically unsuitable as a ratio;
   it remains an unresolved supporting observation and does not affect the signal.
3. Reopen v1 only if repeated failures emerge across multiple companies or tracked
   realized-performance evidence.
