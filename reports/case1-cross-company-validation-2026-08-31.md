# Case 1 Cross-company Validation — 2026-08-31

Status: VALIDATION

Authoritative for Results: YES

Authoritative for Investment Rules: NO — see [Case 1 v1](../docs/specs/case1-v1.md)

## Purpose

This table compares five companies through the same Case 1 normalization,
metric, grading, and scoring path. Values are raw metric outputs followed by the
absolute grade in parentheses. Capital Model labels do not adjust any result.

| Ticker | Capital Model | Revenue Growth | Operating Profit Growth | Margin Trend | Cash Economics | Capital Efficiency | Balance Sheet | Dilution | Per-share Growth | Quant Score | Quant Grade |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| STRL | project_based | 12.0618% (C) | 36.4237% (A) | +7.2664 pp (A) | 1.9567x (A) | 41.3514% (A) | -0.2073x (A) | 0.4160% (B) | 43.7160% (A) | **3.650** | **A** |
| ORCL | capital_intensive | 10.4767% (C) | 16.3192% (C) | +4.3821 pp (A) | 1.7869x (A) | 14.7557% (B) | 3.2860x (D) | 1.7527% (B) | 23.8350% (B) | **2.700** | **C** |
| 003230.KS | manufacturing | 37.2794% (A) | 79.6713% (A) | +12.3470 pp (A) | 1.0620x (A) | 36.0978% (A) | 0.1810x (A) | -0.0692% (A) | 69.7388% (A) | **4.000** | **A** |
| LLY | rd_ip_driven | 31.6874% (A) | 54.5330% (A) | +15.3817 pp (A) | 0.8190x (B) | 39.6515% (A) | 1.2451x (B) | -0.1964% (A) | 49.2718% (A) | **3.800** | **A** |
| 010120.KS | manufacturing | 13.7146% (C) | 31.4990% (A) | +3.0340 pp (A) | 1.0144x (A) | 11.5349% (C) | 1.0375x (B) | 0.4116% (B) | 46.3597% (A) | **3.150** | **B** |

## Repeated observations

- The pipeline handles USD millions and reported KRW units through the existing
  normalization layer and sorts shuffled inputs by fiscal-period end.
- EBITDA is not a standardized GAAP subtotal. ORCL, Samyang, Lilly, and LS
  ELECTRIC therefore use documented derivations in `supplied_ebitda`, while the
  schema does not preserve component-level derivation provenance.
- Debt-component boundaries require an explicit normalization convention. The
  Korean fixtures use interest-bearing borrowings and exclude lease liabilities,
  consistent with standardized ROIC v1, but that choice is only documented.
- Absolute ROIC permits direct reproducibility but does not account for R&D,
  goodwill, leases, excess cash, sector, or Capital Model differences.
- The shared trend label can say decelerating while the absolute growth grade is
  A. It is supporting information and does not adjust the score.

## Potential common issues; no engine change made

Two or more companies expose incomplete field-level provenance for derived
EBITDA and ambiguity about which debt components belong in `total_debt`. These
are normalization/provenance issues, not evidence that a Core metric or grading
threshold should change. A later input-layer revision could encode derivation
components and debt inclusion policy without adding a ninth Core metric.

No repeated result in this sample justifies changing Case 1 formulas, weights,
or grade bands. Valuation, Narrative, and Investment Grade remain out of scope.
