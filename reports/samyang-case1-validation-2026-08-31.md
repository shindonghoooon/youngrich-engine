# Samyang Foods Case 1 Validation — 2026-08-31

## Scope and sources

This is a reproducible Quant Quality validation of the existing Case 1 engine.
No threshold, formula, weight, or company-specific exception was changed.

- Ticker: `003230.KS`
- Capital Model: `manufacturing` (descriptive only; no benchmark adjustment)
- Periods: FY2022–FY2025, each ending December 31
- Unit: KRW, stored as reported won
- Official consolidated audit reports: [FY2025](https://www.samyangfoods.com/upload/ir/20260318/20260318164557921390.pdf), [FY2024](https://www.samyangfoods.com/upload/ir/20250318/20250318174220317203.pdf), and [FY2023](https://www.samyangfoods.com/upload/ir/20240320/20240320183605807005.pdf)

## Raw financial inputs

Amounts are KRW billions except shares and EPS; displayed values are rounded
but the fixture preserves reported won.

| Field | FY2022 | FY2023 | FY2024 | FY2025 |
|---|---:|---:|---:|---:|
| Revenue | 909.0 | 1,192.9 | 1,728.0 | 2,351.8 |
| Operating income | 90.4 | 147.5 | 344.6 | 524.2 |
| Pretax income | 102.0 | 156.3 | 351.6 | 516.9 |
| Income tax expense | 21.7 | 29.7 | 80.4 | 128.2 |
| Consolidated net income | 80.3 | 126.6 | 271.3 | 388.7 |
| Common-attributable net income | 79.8 | 126.3 | 272.0 | 389.4 |
| CFO | 47.8 | 168.1 | 357.9 | 309.3 |
| CAPEX (property, plant and equipment) | 86.9 | 45.0 | 228.5 | 449.0 |
| Cash and cash equivalents | 96.9 | 218.7 | 334.8 | 332.8 |
| Borrowings used as total debt | 273.0 | 307.5 | 312.8 | 439.3 |
| Total equity | 454.8 | 576.8 | 828.0 | 1,271.5 |
| Diluted weighted shares | 7,482,262 | 7,458,128 | 7,458,128 | 7,466,745 |
| Diluted EPS (KRW) | 10,665 | 16,929 | 36,468 | 52,156 |

FY2025 supplied EBITDA is KRW 587.9 billion: operating income of KRW 524.2
billion plus reported depreciation and amortization of KRW 63.7 billion.
Debt includes short-term borrowings, the current portion of long-term
borrowings, and long-term borrowings; lease liabilities are excluded under the
existing standardized ROIC v1 convention.

## Case 1 Quant Snapshot

| Core metric | Raw value | Grade | Weight | Trend / tag |
|---|---:|:---:|---:|---|
| Revenue Growth | 37.2794% 3Y CAGR | A | 15% | stable |
| Operating Profit Growth | 79.6713% 3Y CAGR | A | 15% | decelerating |
| Margin Trend | +12.3470 pp | A | 10% | — |
| Cash Economics | 1.0620x | A | 10% | `high` reinvestment |
| Capital Efficiency | 36.0978% ROIC | A | 20% | decelerating |
| Balance Sheet | 0.1810x Net Debt/EBITDA | A | 10% | — |
| Dilution | -0.0692% 3Y CAGR | A | 5% | — |
| Per-share Growth | 69.7388% 3Y CAGR | A | 15% | — |

- Quant Score: **4.000**
- Quant Grade: **A**
- Metrics / weights: **8 / 1.000**

## Calculation detail

- Cash Economics uses FY2023–FY2025 CFO of KRW 835.3 billion divided by
  consolidated net income of KRW 786.5 billion: **1.0620x**.
- FY2023–FY2025 CAPEX is KRW 722.4 billion; CAPEX/CFO is **0.8649x**, producing
  the **`high`** tag. The tag does not alter the Cash Economics grade.
- FY2025 effective tax rate is 128.2 / 516.9 = **24.8009%**.
- FY2024 invested capital is KRW 806.0 billion and FY2025 is KRW 1,378.0
  billion. Average invested capital is KRW 1,092.0 billion.
- FY2025 NOPAT is KRW 394.2 billion, producing **36.0978% ROIC**. Previous-year
  ROIC is **36.1234%**; the small decline only sets the trend.
- FY2025 net debt is KRW 106.4 billion; divided by derived EBITDA of KRW 587.9
  billion, Net Debt/EBITDA is **0.1810x**.

## Distortion observations and unresolved items

- The all-A result follows the unchanged absolute rules. It does not incorporate
  export mix, Buldak penetration, capacity, or channel durability.
- The operating-profit trend is marked decelerating even though growth remains
  very high, because the shared trend helper compares latest YoY growth with the
  three-year CAGR. That label is descriptive and does not alter the grade.
- `supplied_ebitda` is reproducibly derived, but the schema does not separately
  encode its depreciation/amortization components.
- The debt convention excludes lease liabilities and does not attempt excess-cash
  or goodwill adjustments. No Samyang-specific correction was introduced.

