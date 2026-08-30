# Cash Economics v1

Cash Economics는 Profitable Growth의 고정된 8개 Core 중 하나다.

## Primary grade

3개년 누적 현금흐름을 사용한다.

```text
cash conversion = cumulative CFO / cumulative net income
```

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
