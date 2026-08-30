# Financial Input / Normalization Layer v1

## Pipeline

```text
Raw Data
  -> Normalization
  -> Metrics
  -> Case Grading
  -> Quant Snapshot
  -> Valuation / Narrative
  -> Investment Grade
```

`data/raw/`의 원재무 데이터와 source metadata가 입력 정본이다. 금액은 fixture의
`unit_scale`로 해석한 뒤 `FinancialHistory`에서 통화 기본 단위로 정규화한다.
`FinancialHistory.periods`는 `fiscal_period_end` 오름차순으로 정렬된다.
`fiscal_year`는 회사가 보고한 FY label이며 달력연도와 같다고 가정하지 않는다.

생성된 `AnalysisSnapshot`은 raw data가 아니다. 계산 규칙이나 입력 데이터가 바뀌면
언제든 다시 생성할 수 있는 파생 결과다. 보고서와 Dashboard도 snapshot을 렌더링할
뿐 정본이 아니다.

## STRL v1 conventions

- 기간: FY2022-FY2025 연간 데이터
- 금액/희석주식수 raw unit: thousands
- 통화: USD
- 성장률과 margin 변화: FY2022에서 FY2025까지 3년
- CAGR 기간 수: 4개 연간 observation 사이의 3개 interval
- 누적 Cash Economics: 최근 3개 기간(FY2023-FY2025)
- CAPEX: 현금 유출의 절댓값을 양수로 저장
- Net Debt / EBITDA: 최신 연말 cash, total debt와 공식 발표 EBITDA 사용
- 2022 net income과 diluted EPS: continuing operations 기준

## ROIC unresolved

ROIC는 계산 정의에 따라 결과가 크게 달라질 수 있다. v1은 임의의 공식을 엔진에
고정하지 않고 공식 또는 별도 검증된 `supplied_roic`만 허용한다. STRL의 SEC 공시에서
공식 ROIC를 확인하지 못했으므로 fixture에는 `null`을 저장했다. 따라서 현재 STRL
snapshot은 Capital Efficiency grade와 최종 Quant Score/Grade를 확정하지 않는다.

이는 결측치를 X로 오인해 감점하거나 provisional 결과를 정답으로 복사하는 것을
막기 위한 의도적인 incomplete 상태다.
