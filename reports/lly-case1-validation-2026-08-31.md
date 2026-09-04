# Eli Lilly Case 1 Validation — 2026-08-31

Status: VALIDATION

Authoritative for Results: YES

Authoritative for Investment Rules: NO — see [Case 1 v1](../docs/specs/case1-v1.md)

## Scope and sources

This report reuses the existing Case 1 pipeline and absolute rules without an
R&D capitalization, acquired-IPR&D, patent, product, or pipeline adjustment.

- Ticker: `LLY`
- Capital Model: `rd_ip_driven` (descriptive only)
- Periods: FY2022–FY2025, each ending December 31
- Unit: USD millions
- Official sources: Lilly [FY2025 Form 10-K](https://investor.lilly.com/static-files/0d64699c-0cc7-490e-9152-b2ba1de08634), [FY2024 Form 10-K](https://investor.lilly.com/static-files/84711071-9e5a-47e1-bc74-d0753a2d93a8), [FY2025 results](https://investor.lilly.com/news-releases/news-release-details/lilly-reports-fourth-quarter-2025-financial-results-and-provides), [FY2024 results](https://investor.lilly.com/news-releases/news-release-details/lilly-reports-full-q4-2024-financial-results-and-provides-2025), [FY2023 results](https://investor.lilly.com/node/50281), and [SEC company facts](https://data.sec.gov/api/xbrl/companyfacts/CIK0000059478.json)

The 10-K supplies the GAAP statements. Lilly's official earnings releases supply
the reported operating-income subtotal, which the 10-K does not present as a
standalone line.

## Raw financial inputs

| Field (USD millions) | FY2022 | FY2023 | FY2024 | FY2025 |
|---|---:|---:|---:|---:|
| Revenue | 28,541.4 | 34,124.1 | 45,042.7 | 65,179.0 |
| Operating income | 7,127.3 | 6,457.9 | 12,899.0 | 26,302.0 |
| Pretax income | 6,806.4 | 6,554.6 | 12,680.4 | 25,731.0 |
| Income tax expense | 561.6 | 1,314.2 | 2,090.4 | 5,091.0 |
| Consolidated / common net income | 6,244.8 | 5,240.4 | 10,590.0 | 20,640.0 |
| CFO | 7,585.7 | 4,240.1 | 8,817.9 | 16,813.0 |
| CAPEX | 1,854.3 | 3,447.6 | 5,057.8 | 7,841.0 |
| Cash and cash equivalents | 2,067.0 | 2,818.6 | 3,268.4 | 7,268.0 |
| Total debt | 16,238.6 | 25,225.3 | 33,644.2 | 42,503.0 |
| Total equity including NCI | 10,775.4 | 10,863.7 | 14,271.6 | 26,535.0 |
| Diluted weighted shares (millions) | 904.619 | 903.284 | 904.059 | 899.300 |
| Diluted EPS (USD) | 6.90 | 5.80 | 11.71 | 22.95 |

FY2025 supplied EBITDA is USD 28,299 million: operating income of USD 26,302
million plus reported depreciation and amortization of USD 1,997 million.

## Case 1 Quant Snapshot

| Core metric | Raw value | Grade | Weight | Trend / tag |
|---|---:|:---:|---:|---|
| Revenue Growth | 31.6874% 3Y CAGR | A | 15% | accelerating |
| Operating Profit Growth | 54.5330% 3Y CAGR | A | 15% | accelerating |
| Margin Trend | +15.3817 pp | A | 10% | — |
| Cash Economics | 0.8190x | B | 10% | `moderate` reinvestment |
| Capital Efficiency | 39.6515% ROIC | A | 20% | accelerating |
| Balance Sheet | 1.2451x Net Debt/EBITDA | B | 10% | — |
| Dilution | -0.1964% 3Y CAGR | A | 5% | — |
| Per-share Growth | 49.2718% 3Y CAGR | A | 15% | — |

- Quant Score: **3.800**
- Quant Grade: **A**
- Metrics / weights: **8 / 1.000**

## Calculation detail

- FY2023–FY2025 CFO is USD 29,871.0 million and consolidated net income is USD
  36,470.4 million, producing **0.8190x CFO conversion**.
- CAPEX is USD 16,346.4 million; CAPEX/CFO is **0.5472x**, producing the
  **`moderate`** tag without changing the B Cash Economics grade.
- FY2025 effective tax rate is 5,091 / 25,731 = **19.7855%**.
- FY2024/FY2025 invested capital is USD 44,647.4 / 61,770.0 million; average
  invested capital is USD 53,208.7 million.
- FY2025 NOPAT is USD 21,098.0 million and ROIC is **39.6515%**. Previous-year
  ROIC is **27.6511%**.
- FY2025 net debt is USD 35,235 million. Net Debt/derived EBITDA is **1.2451x**.

## Distortion observations and unresolved items

- The standardized accounting ROIC is intentionally not adjusted for R&D or
  acquired IPR&D, so it should not be read as an economic return on all drug
  discovery investment.
- CFO conversion is below 1.0x during a rapid manufacturing expansion. CAPEX is
  only a supporting tag and does not directly reduce the grade.
- Reported operating income requires a second official source because the 10-K
  has no subtotal. This is a provenance issue, not a company-specific metric.
- `supplied_ebitda` derivation components remain documented rather than encoded
  as structured fields. No Lilly-specific adjustment was added.
