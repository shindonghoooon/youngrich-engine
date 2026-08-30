# Case 1 Stress Test — 2026-08-30

## Status

이 문서는 Case 1 규칙을 실제 기업에 적용해 본 **provisional calibration report**다.
These results are provisional manual validation results and are not yet
reproducible from raw financial inputs stored in this repository.
구조화된 원재무 입력과 출처가 저장소에 추가되기 전까지 아래 결과를 source of
truth로 사용하지 않는다.

## Provisional ranking

| Rank | Company | Quant Score | Quant Grade |
|---:|---|---:|---|
| 1 | Samyang Foods | 4.00 | A |
| 2 | Eli Lilly | 3.80 | A |
| 3 | Sterling Infrastructure | 3.65 | A |
| 4 | LS ELECTRIC | 3.05 | B |
| 5 | Oracle | 2.60 | C |

이 랭킹에는 Valuation과 Narrative를 섞지 않았다. 따라서 Quant Quality 순위이며
Investment Grade 순위가 아니다.

## Router control

SK hynix는 높은 최근 성장률과 수익성에도 불구하고 메모리 산업의 구조적 사이클이
현재 경제성을 지배하므로 Case 1 점수를 계산하지 않는다. Router가 먼저
`cyclical`로 보내야 하며 `data/examples/SK_HYNIX.router-test.json`을 회귀 fixture로
둔다.

## Decisions locked by this test

1. Profitable Growth의 Core는 8개로 고정한다.
2. Cash Economics primary는 3년 누적 CFO / 3년 누적 순이익이다.
3. CAPEX / CFO는 grade 감점 요소가 아니라 reinvestment intensity 태그다.
4. Capital Model benchmark는 충분한 표본 전까지 점수에 적용하지 않는다.
5. Narrative는 Quant grade를 변경하지 않는다.

## Data required before promotion

각 회사별로 동일 회계기준의 3개년 원재무 데이터, 희석주식수, ROIC 계산 입력,
Net Debt / EBITDA 및 출처를 구조화해 저장한 뒤 결과를 재실행해야 한다. 그때 현재
점수와 차이가 나면 보고서 숫자가 아니라 재현 가능한 엔진 결과를 우선한다.
