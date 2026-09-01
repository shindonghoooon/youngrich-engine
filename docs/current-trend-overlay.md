# Current Trend Overlay v1

## 역할

`Quant Grade`는 검증된 연간 재무 품질이고, `Current Trend`는 최신 영업 방향이다.
Current Trend는 별도 signal layer이며 Annual Quant Score와 Grade를 수정하지 않는다.

```text
Official Annual Financials -> Annual Base Quant -> Quant Score / Grade
Official Current Periods   -> Current Trend Overlay
                                      ↓
                                  Valuation
                                      ↓
                    Narrative / Expectation Gap / Risk
                                      ↓
                               Investment Grade
```

v1은 기존 Core 중 Revenue Growth, Operating Profit Growth, Margin Trend, Cash
Economics, Balance Sheet의 방향만 평가한다. 분기 ROIC, Dilution, EPS CAGR은 기간
불일치와 회계 노이즈 때문에 Annual Base에 남긴다. 새로운 Core나 Current Grade는
추가하지 않는다.

## 입력과 no-look-ahead

`CurrentFinancialPeriod`는 `quarter`, `ytd`, `ttm` 중 하나이며 current와
prior-year comparable period의 유형이 같아야 한다. `period_end`와 모든 공식
source의 filing/release date는 overlay `as_of`보다 늦을 수 없다. 통화 단위는 annual
history와 동일하게 정규화하고, filing date와 retrieved timestamp를 보존한다.

Balance Sheet에는 current quarter-end cash/debt와 재현 가능한 current TTM EBITDA가
모두 있을 때만 Net Debt/EBITDA를 계산한다. Annual EBITDA와 current debt를 섞지
않으며, EBITDA가 없으면 `unresolved`다.

## Signal rules

| Signal | Positive | Neutral | Negative |
|---|---|---|---|
| Revenue growth | Current YoY > annual 3Y CAGR + 5pp | annual CAGR ±5pp | Current YoY < annual CAGR − 5pp |
| Operating profit growth | Current YoY > annual 3Y CAGR + 5pp | annual CAGR ±5pp | Current YoY < annual CAGR − 5pp |
| Margin trend | comparable margin change ≥ +1pp | between −1pp and +1pp | change ≤ −1pp |
| Cash Economics | current conversion ≥ annual ×1.10 | annual ×0.90 through ×1.10 | current < annual ×0.90 |
| Balance Sheet | ratio improves by ≥0.5x | change within ±0.5x | ratio worsens by ≥0.5x |

Current CAPEX/CFO is recorded in the Cash Economics observation only. CAPEX
intensity does not create a negative signal.

Overall is not scored:

- at least three positive and no negative: `positive`
- at least three negative and no positive: `negative`
- at least two positive and two negative: `mixed`
- fewer than three resolved sub-signals: `unresolved`
- otherwise: `neutral`

## First validation: STRL 2026 Q2 / H1

Official inputs are the [2026 Q2 Form 10-Q](https://www.sec.gov/Archives/edgar/data/874238/000087423826000103/strl-20260630.htm), filed 2026-08-04, and the [Q2 earnings release](https://www.sec.gov/Archives/edgar/data/874238/000087423826000100/a20260803ex991earningsrele.htm), released 2026-08-03.

- Revenue Growth: `positive`
- Operating Profit Growth: `positive`
- Margin Trend: `positive`
- Cash Economics: `negative`
- Balance Sheet: `neutral`
- Overall: `neutral`

The overall result is deliberately neutral under the frozen rule because three
positive signals coexist with one negative. The Cash Economics decline partly
reflects comparison with an unusually high annual conversion base. Acquisitions
also contribute to current growth. These observations do not trigger an STRL
exception or a threshold change.

The TTM EBITDA input is reproducible as FY2025 EBITDA plus H1 2026 EBITDA minus
H1 2025 EBITDA: 472.000 + 388.763 − 188.315 = USD 672.448 million.
