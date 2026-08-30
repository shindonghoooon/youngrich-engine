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

## Capital Efficiency

ROIC는 `operating_income`, `pretax_income`, `income_tax_expense`, `total_debt`,
`total_equity`, `cash`에서 자동 계산한다. 공식과 unresolved guardrail은
[Capital Efficiency v1](capital-efficiency.md)을 따른다.
