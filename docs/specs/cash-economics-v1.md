# Cash Economics v1

Status: FROZEN

Version: 1.0

Authoritative: YES

Last Updated: 2026-09-04

Implementation: `engine/financial_metrics.py`, `engine/cases/profitable_growth.py`

Tests: `tests/test_financial_pipeline.py`, `tests/test_scoring.py`

Supersedes: `docs/cash-economics.md`

Change Policy: changes require an explicit design decision and version bump.

Cash Economics는 Profitable Growth의 고정된 8개 Core 중 하나다.

## Primary grade

3개년 누적 현금흐름을 사용한다.

```text
cash conversion = cumulative consolidated CFO / cumulative consolidated net income
```

Cash Economics는 연결 영업현금흐름과 연결 순이익을 비교한다. 지배기업 보통주주
귀속 순이익(`net_income_common`)은 회계 범위가 다르므로 CFO conversion에 사용하지
않고 shareholder-level supporting data로만 보존한다.

Cash Economics compares consolidated operating cash flow with consolidated net income.
Common-shareholder attributable net income is not used for CFO conversion because the
accounting scopes would differ.

| Cash conversion | Grade |
|---:|---|
| >= 1.00x | A |
| >= 0.80x | B |
| >= 0.60x | C |
| >= 0.40x | D |
| < 0.40x | X |

누적 순이익이 0 이하라면 이 판정은 의미가 없으므로 X로 처리한다. 이 경우에는
Case Router가 Profitable Growth 적합성을 먼저 재검토해야 한다.

## Reinvestment tag

```text
reinvestment intensity = abs(cumulative CAPEX) / cumulative CFO
```

| Intensity | Tag |
|---:|---|
| >= 1.00x | `very_high` |
| >= 0.60x | `high` |
| >= 0.30x | `moderate` |
| < 0.30x | `low` |

CAPEX intensity는 재투자 상태를 설명하는 태그이며 Cash Economics grade를 직접
낮추지 않는다. 따라서 높은 CFO conversion과 높은 재투자 강도는 동시에 존재할
수 있다. FCF가 음수라는 사실만으로 현금창출 실패로 판정하지 않는다.
