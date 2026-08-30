# ORCL Case 1 Validation — 2026-08-30

## Scope

This report validates the existing Case 1 Profitable Growth pipeline for Oracle
Corporation. It covers Quant Quality only. The pipeline and absolute grading
rules are unchanged from the STRL validation.

- Case: Profitable Growth
- Capital Model: `capital_intensive`
- Benchmark adjustment: not applied
- Source unit: USD millions, normalized to USD units by the shared loader
- Observation window: FY2023 through FY2026, with fiscal years ending May 31

## Official sources

- Oracle FY2026 Form 10-K, filed 2026-06-22:
  <https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm>
- Oracle FY2025 Form 10-K, filed 2025-06-18:
  <https://www.sec.gov/Archives/edgar/data/1341439/000095017025087926/orcl-20250531.htm>
- Oracle FY2023 Form 10-K, filed 2023-06-20:
  <https://www.sec.gov/Archives/edgar/data/1341439/000095017023028914/orcl-20230531.htm>

FY2024 and FY2025 income-statement and cash-flow values use the FY2026 10-K
comparatives where available. The FY2024 balance-sheet values use the FY2025
10-K. FY2023 uses the FY2023 10-K.

## Raw financial inputs

All amounts except per-share data are USD millions. Total equity includes the
portion attributable to noncontrolling interests, matching the standardized
invested-capital input used for STRL.

| Field | FY2023 | FY2024 | FY2025 | FY2026 |
|---|---:|---:|---:|---:|
| Revenue | 49,954 | 52,961 | 57,399 | 67,357 |
| Operating income | 13,093 | 15,353 | 17,678 | 20,606 |
| Pretax income | 9,126 | 11,741 | 14,160 | 19,554 |
| Income tax expense | 623 | 1,274 | 1,717 | 2,467 |
| Consolidated net income | 8,503 | 10,467 | 12,443 | 17,087 |
| Common net income | not supplied | 10,467 | 12,443 | 16,984 |
| CFO | 17,165 | 18,673 | 20,821 | 31,977 |
| CAPEX | 8,695 | 6,866 | 21,215 | 55,663 |
| Cash and cash equivalents | 9,765 | 10,454 | 10,786 | 31,289 |
| Total debt | 90,481 | 86,869 | 92,568 | 129,541 |
| Total equity | 1,556 | 9,239 | 20,969 | 43,056 |
| Diluted shares (millions) | 2,766 | 2,823 | 2,866 | 2,914 |
| Diluted EPS (USD) | 3.07 | 3.71 | 4.34 | 5.83 |

The FY2026 10-K does not report EBITDA as a standalone GAAP line item. The
fixture's `supplied_ebitda` is a reproducible derivation from official FY2026
GAAP values: operating income 20,606 + depreciation 7,623 + intangible
amortization 1,671 = 29,900 million.

## Case 1 Quant Snapshot

| Core metric | Raw value | Grade | Weight | Trend / tag |
|---|---:|:---:|---:|---|
| Revenue Growth | 10.4767% 3Y CAGR | C | 15% | accelerating |
| Operating Profit Growth | 16.3192% 3Y CAGR | C | 15% | stable |
| Margin Trend | +4.3821 pp | A | 10% | — |
| Cash Economics | 1.7869x CFO conversion | A | 10% | `very_high` reinvestment |
| Capital Efficiency | 14.7557% ROIC | B | 20% | decelerating |
| Balance Sheet | 3.2860x Net Debt/EBITDA | D | 10% | — |
| Dilution | 1.7527% diluted-share CAGR | B | 5% | — |
| Per-share Growth | 23.8350% diluted-EPS CAGR | B | 15% | — |

- Weighted Quant Score: **2.700**
- Quant Grade: **C**
- Metrics produced: **8**
- Weights sum: **1.000**

## Calculation details

### Cash Economics

- FY2024–FY2026 cumulative CFO: 71,471 million
- FY2024–FY2026 cumulative consolidated net income: 39,997 million
- CFO conversion: 71,471 / 39,997 = **1.7869x**
- FY2024–FY2026 cumulative CAPEX: 83,744 million
- CAPEX/CFO: 83,744 / 71,471 = **1.1717x**
- Reinvestment tag: **`very_high`**

The CAPEX tag does not change the A Cash Economics grade. Negative free cash
flow caused by the investment program is not used as a separate Core metric.

### Standardized ROIC v1

- FY2026 effective tax rate: 2,467 / 19,554 = **12.6163%**
- FY2025 invested capital: 92,568 + 20,969 − 10,786 = **102,751 million**
- FY2026 invested capital: 129,541 + 43,056 − 31,289 = **141,308 million**
- Average invested capital: (102,751 + 141,308) / 2 = **122,029.5 million**
- FY2026 NOPAT: 20,606 × (1 − 12.6163%) = **18,006.3 million**
- FY2026 ROIC: 18,006.3 / 122,029.5 = **14.7557%**
- Previous-year ROIC: **16.4905%**
- Trend: **decelerating**; the trend does not alter the B grade

### Balance Sheet

- FY2026 net debt: 129,541 − 31,289 = **98,252 million**
- Derived FY2026 EBITDA: **29,900 million**
- Net Debt/EBITDA: 98,252 / 29,900 = **3.2860x**

## Observations and unresolved items

- The same shared normalization, metric, grading, scoring, and snapshot code
  handles a May fiscal year-end without an Oracle-specific path.
- Oracle's large investment program appears in the `very_high` CAPEX intensity
  tag while CFO conversion remains strong. This is the intended separation.
- Absolute standardized ROIC declines despite higher operating income because
  invested capital expands faster. No goodwill, lease, R&D, excess-cash, sector,
  or Capital Model adjustment is applied.
- `supplied_ebitda` can hold the reproducible GAAP-derived value, but the current
  schema cannot encode field-level derivation components. That provenance detail
  remains documented here rather than prompting an Oracle-specific schema change.
- FY2023 `net_income_common` remains null because the optional common-attributable
  value was not separately tagged in the selected FY2023 source. Cash Economics
  correctly uses consolidated net income and is unaffected.
