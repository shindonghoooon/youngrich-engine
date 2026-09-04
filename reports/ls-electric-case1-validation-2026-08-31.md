# LS ELECTRIC Case 1 Validation — 2026-08-31

Status: VALIDATION

Authoritative for Results: YES

Authoritative for Investment Rules: NO — see [Case 1 v1](../docs/specs/case1-v1.md)

## Scope and sources

This report uses only reported financial history. Grid investment, data-center
demand, transformer supply, backlog, and U.S. infrastructure themes are outside
the Quant Snapshot.

- Ticker: `010120.KS`
- Capital Model: `manufacturing` (descriptive only)
- Periods: FY2022–FY2025, each ending December 31
- Unit: KRW, stored as reported won
- Official source directory: [LS ELECTRIC audit reports](https://www.ls-electric.com/ko/company/invest/result-audit)
- Consolidated report archives: [FY2025](https://www.ls-electric.com/ko/company/invest/data/LS_ELECTRIC_2025%EB%85%84_%EC%97%B0%EA%B2%B0.zip), [FY2024](https://www.ls-electric.com/ko/company/invest/data/LS_ELECTRIC_2024%EB%85%84_%EC%97%B0%EA%B2%B0.zip), [FY2023](https://www.ls-electric.com/ko/company/invest/data/LS_ELECTRIC_2023%EB%85%84_%EC%97%B0%EA%B2%B0.zip), and [FY2022](https://www.ls-electric.com/ko/company/invest/data/LS_ELECTRIC_2022%EB%85%84_%EC%97%B0%EA%B2%B0.zip)

## Raw financial inputs

Amounts are KRW billions except shares and EPS; the fixture stores exact won.

| Field | FY2022 | FY2023 | FY2024 | FY2025 |
|---|---:|---:|---:|---:|
| Revenue | 3,377.1 | 4,230.5 | 4,551.8 | 4,965.8 |
| Operating income | 187.5 | 324.9 | 389.7 | 426.4 |
| Pretax continuing income | 127.0 | 264.1 | 333.4 | 410.1 |
| Continuing income tax expense | 35.0 | 56.1 | 91.1 | 125.8 |
| Consolidated net income | 91.2 | 207.7 | 242.2 | 284.3 |
| Common-attributable net income | 90.3 | 206.0 | 238.7 | 286.6 |
| CFO | -145.4 | 214.6 | 230.1 | 299.9 |
| CAPEX (property, plant and equipment) | 114.9 | 112.9 | 145.2 | 200.9 |
| Cash and cash equivalents | 556.1 | 583.9 | 660.1 | 762.7 |
| Borrowings used as total debt | 876.5 | 931.6 | 1,174.0 | 1,342.4 |
| Total equity | 1,549.3 | 1,724.0 | 1,890.1 | 2,141.3 |
| Diluted weighted shares | 29,348,482 | 29,370,821 | 29,551,721 | 29,712,376 |
| Diluted EPS (KRW) | 3,077 | 7,012 | 8,078 | 9,647 |

FY2025 supplied EBITDA is KRW 558.7 billion: operating income of KRW 426.4
billion plus depreciation and amortization of KRW 132.3 billion. Total debt is
short-term borrowings plus current and non-current long-term borrowings; lease
liabilities and the convertible redeemable preference liability are excluded.

## Case 1 Quant Snapshot

| Core metric | Raw value | Grade | Weight | Trend / tag |
|---|---:|:---:|---:|---|
| Revenue Growth | 13.7146% 3Y CAGR | C | 15% | decelerating |
| Operating Profit Growth | 31.4990% 3Y CAGR | A | 15% | decelerating |
| Margin Trend | +3.0340 pp | A | 10% | — |
| Cash Economics | 1.0144x | A | 10% | `high` reinvestment |
| Capital Efficiency | 11.5349% ROIC | C | 20% | decelerating |
| Balance Sheet | 1.0375x Net Debt/EBITDA | B | 10% | — |
| Dilution | 0.4116% 3Y CAGR | B | 5% | — |
| Per-share Growth | 46.3597% 3Y CAGR | A | 15% | — |

- Quant Score: **3.150**
- Quant Grade: **B**
- Metrics / weights: **8 / 1.000**

## Calculation detail

- FY2023–FY2025 CFO is KRW 744.7 billion and consolidated net income is KRW
  734.2 billion, producing **1.0144x CFO conversion**.
- CAPEX is KRW 459.0 billion; CAPEX/CFO is **0.6163x**, producing the **`high`**
  tag without altering the A Cash Economics grade.
- FY2025 effective tax rate is 125.8 / 410.1 = **30.6810%**.
- FY2024/FY2025 invested capital is KRW 2,404.0 / 2,721.0 billion; average
  invested capital is KRW 2,562.5 billion.
- FY2025 NOPAT is KRW 295.6 billion and ROIC is **11.5349%**. Previous-year ROIC
  is **12.6532%**.
- FY2025 net debt is KRW 579.7 billion. Net Debt/derived EBITDA is **1.0375x**.

## Distortion observations and unresolved items

- FY2022's negative CFO is outside the trailing three periods used by Cash
  Economics. The four-year fixture preserves it, but the metric intentionally
  evaluates FY2023–FY2025 only.
- A large portion of EPS growth reflects the low FY2022 base; backlog and future
  infrastructure demand are not used to raise the score.
- EBITDA adds reported right-of-use-asset amortization while debt excludes lease
  liabilities under current v1 conventions. That denominator/debt scope should
  be tracked across companies, not corrected only for LS ELECTRIC.
- The C Capital Efficiency grade is the result of unchanged absolute ROIC bands.
  No manufacturing benchmark adjustment was applied.
