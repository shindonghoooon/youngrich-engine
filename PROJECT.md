# Project Rules

## Objective

이 프로젝트의 목적은 단순히 좋은 기업을 분류하는 것이 아니다.

> 좋은 기업을 합리적인 가격에 골라내고, 실제 투자 성과를 추적하여
> 분석 로직의 적중률과 기대수익률을 지속적으로 개선한다.

## Fixed Design Principles

### 1. No stock-specific Quant rules

특정 종목 분석 중 발견된 특이사항을 공통 Quant Core에 추가하지 않는다.

예:
- STRL backlog
- SK hynix HBM
- Eli Lilly GLP-1
- Samyang Buldak export penetration

이들은 모두 Narrative / Tracking에서 다룬다.

### 2. Quant and Narrative are separated

Narrative는 Quant Grade를 직접 수정하지 않는다.

```text
Quant Quality
+
Valuation
+
Narrative / Expectation Gap
+
Risk
=
Investment Grade
```

### 3. Capital Model modifies interpretation, not the indicator set

동일한 8개 Core를 모든 Profitable Growth 기업에 사용한다.

Capital Model:
- asset_light
- manufacturing
- capital_intensive
- project_based
- rd_ip_driven

Capital Model은 benchmark 및 해석을 조정할 수 있지만 새로운 지표를 만들지 않는다.

### 4. Case Router runs before Case Quant

기업의 현재 투자 thesis에 적합한 Case를 먼저 판정한다.

예:
SK hynix는 최근 성장률이 높더라도 메모리 산업의 구조적 사이클이 지배적이면
Profitable Growth가 아니라 Cyclical / Mean Reversion으로 보낸다.

### 5. Structured data is the source of truth

Markdown 보고서가 분석 결과의 정본이 아니다.

분석 결과는 구조화된 데이터 / DB가 정본이며,
Dashboard와 Report는 해당 데이터를 렌더링한다.

## Case Taxonomy

1. profitable_growth
2. loss_making_growth
3. cyclical
4. quality_compounder
5. largecap_value
6. asset_special

새 Case는 기존 6개로 경제구조를 반복적으로 설명할 수 없는 기업군이 확인될 때만 추가한다.

## Workflow

1. Route case
2. Assign capital model
3. Collect standardized metrics
4. Run case Quant engine
5. Evaluate valuation
6. Write narrative
7. Define kill / tracking items
8. Produce final investment grade
9. Save snapshot
10. Track future earnings and realized performance

## Change Policy

- 종목 하나 때문에 rule 변경 금지
- 공통적인 실패가 여러 종목에서 반복될 때만 수정 검토
- 로직 변경 시 기존 테스트 종목을 모두 재실행
- 실제 성과 데이터와 함께 변경 이유를 기록
