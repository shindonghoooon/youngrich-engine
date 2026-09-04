# Capital Efficiency v1

Status: FROZEN

Version: 1.0

Authoritative: YES

Last Updated: 2026-09-04

Implementation: `engine/financial_metrics.py`, `engine/cases/profitable_growth.py`

Tests: `tests/test_financial_pipeline.py`

Supersedes: `docs/capital-efficiency.md`

Change Policy: changes require an explicit design decision and version bump.

Capital Efficiency는 Case 1 Profitable Growth의 고정된 8개 Core 중 하나다. v1은
reported accounting data만 사용하는 단순하고 재현 가능한 standardized ROIC를
Primary grade input으로 사용한다.

## Formula

```text
Effective Tax Rate = Income Tax Expense / Pretax Income
NOPAT = Operating Income × (1 - Effective Tax Rate)
Invested Capital = Total Debt + Total Equity - Cash and Cash Equivalents
Average Invested Capital = (Beginning Invested Capital + Ending Invested Capital) / 2
ROIC = NOPAT / Average Invested Capital
```

최신 ROIC가 grade input이다. 직전 연도 ROIC와 ROIC trend는 supporting information이며
grade를 자동 조정하지 않는다. grade cutoff는 기존 `grade_roic()`만 사용한다.

## Guardrails

- Pretax Income이 0 이하이면 unresolved
- Effective Tax Rate가 0% 미만 또는 40% 초과이면 unresolved
- Average Invested Capital이 0 이하이면 unresolved
- 비정상 세율을 임의로 보정하지 않음
- Capital Model 또는 sector benchmark 조정을 적용하지 않음

## Intentionally excluded

- excess cash adjustment
- goodwill adjustment
- operating lease capitalization
- R&D capitalization
- negative working capital adjustment
- sector normalization
- Capital Model benchmark

여러 기업에서 동일한 왜곡이 반복적으로 확인될 때만 공통 공식의 개선을 검토한다.
