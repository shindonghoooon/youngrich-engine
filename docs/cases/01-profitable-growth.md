# Case 1 — Profitable Growth

## Definition

이미 흑자를 내고 있으며, 사업 성장과 이익 성장이 주당 가치 증가로 이어지는 기업.

핵심 질문:

> 성장의 규모와 지속성이 충분하고,
> 자본 효율성과 주주 경제성을 훼손하지 않으면서 성장하고 있는가?

## Quant Core

### Weight

| Metric | Weight |
|---|---:|
| Revenue Growth | 15% |
| Operating Profit Growth | 15% |
| Margin Trend | 10% |
| Cash Economics | 10% |
| Capital Efficiency | 20% |
| Balance Sheet | 10% |
| Dilution | 5% |
| Per-share Growth | 15% |

가중치는 v1에서 고정한다.

Capital Model은 가중치보다 benchmark 조정을 우선한다.

## 1. Revenue Growth

Primary:
- 3Y Revenue CAGR

Supporting:
- TTM YoY
- Latest quarter YoY

Base grade:
- A: >= 25%
- B: 15% ~ 25%
- C: 8% ~ 15%
- D: 0% ~ 8%
- X: < 0%

Trend:
- Accelerating
- Stable
- Decelerating

Trend는 v1에서 점수를 직접 변경하지 않고 표시한다.

## 2. Operating Profit Growth

Primary:
- 3Y Operating Income CAGR

Base grade:
- A: >= 30%
- B: 18% ~ 30%
- C: 8% ~ 18%
- D: 0% ~ 8%
- X: < 0%

## 3. Margin Trend

Primary:
- Operating Margin change over 3 years

Base:
- A: >= +3%p
- B: +1%p ~ +3%p
- C: -1%p ~ +1%p
- D: -3%p ~ -1%p
- X: < -3%p

Important:
절대 margin이 구조적으로 높은 기업이 높은 수준을 유지하는 경우
Capital Model benchmark를 통해 최소 B까지 보정 가능하다.

## 4. Cash Economics

Inputs:
- 3Y cumulative CFO / 3Y cumulative Net Income
- 3Y cumulative CAPEX / 3Y cumulative CFO

목적:
FCF가 낮다는 사실만으로 quality를 낮게 평가하지 않는다.

구분:
- strong cash generation
- growth reinvestment
- weak conversion
- cash drain

v1 grade는 3Y cumulative CFO / 3Y cumulative Net Income만으로 판정한다.
CAPEX / CFO는 `reinvestment intensity` 태그로 저장하며 grade를 직접 변경하지 않는다.
세부 cutoff와 예외 처리는 [Cash Economics v1](../cash-economics.md)을 따른다.

예:
Oracle처럼 CFO는 강하지만 대규모 AI/cloud CAPEX로 FCF가 음수인 경우
현금창출 실패와 재투자를 구분해야 한다.

## 5. Capital Efficiency

Primary:
- ROIC

Supporting:
- Previous-year ROIC
- Latest ROIC
- ROIC trend

Base:
- A: >= 20%
- B: 12% ~ 20%
- C: 8% ~ 12%
- D: 5% ~ 8%
- X: < 5%

NOTE:
v1은 reported accounting data 기반 standardized ROIC를 사용하며 Capital Model
benchmark adjustment를 적용하지 않는다. 세부 공식은
[Capital Efficiency v1](../capital-efficiency.md)을 따른다.

## 6. Balance Sheet

Primary:
- Net Debt / EBITDA

Base:
- Net cash: A
- 0x ~ 1x: A
- 1x ~ 2x: B
- 2x ~ 3x: C
- 3x ~ 4x: D
- > 4x: X

Capital Model adjustment maximum +/- 1 grade.

## 7. Dilution

Primary:
- 3Y diluted share count CAGR

Base:
- A: <= 0%
- B: 0% ~ 2%
- C: 2% ~ 5%
- D: 5% ~ 10%
- X: > 10%

Capital Model adjustment 없음.

## 8. Per-share Growth

Primary:
- 3Y diluted EPS CAGR

Supporting:
- FCF/share CAGR

Base:
- A: >= 25%
- B: 15% ~ 25%
- C: 8% ~ 15%
- D: 0% ~ 8%
- X: < 0%

## Quant Score

Grade score:
- A = 4
- B = 3
- C = 2
- D = 1
- X = 0

Weighted score maximum: 4.0

Provisional boundaries:
- A: >= 3.50
- B: 3.00 ~ 3.49
- C: 2.40 ~ 2.99
- D: 1.80 ~ 2.39
- X: < 1.80

이 경계값은 calibration 전 임시값이다.

## Narrative

Quant 완료 후 다음 5개 질문만 작성한다.

1. Why Growth?
2. Why Continue?
3. Why This Company?
4. What Is Market Missing?
5. What Breaks The Thesis?

Narrative는 Quant Grade를 수정하지 않는다.

## Output

```text
CASE
CAPITAL MODEL
QUANT QUALITY
VALUATION
NARRATIVE
RISKS
EXPECTATION GAP
TRACK
INVESTMENT GRADE
```
