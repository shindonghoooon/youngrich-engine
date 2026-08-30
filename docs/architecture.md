# Architecture

## Layer 1 — Case Router

투자 아이디어의 경제구조를 분류한다.

현재 정의된 Case:
- Profitable Growth
- Loss-making Growth
- Cyclical / Mean Reversion
- Quality Compounder
- Large-cap Value / Mature Quality
- Asset / Special Situation

Router는 회사의 섹터가 아니라 **현재 earnings / capital / valuation thesis**를 기준으로 한다.

## Layer 2 — Capital Model

Capital Model은 산업/사업 구조에 따라 Quant 지표의 benchmark를 보정한다.

- Asset-light
- Manufacturing
- Capital-intensive
- Project-based
- R&D/IP-driven

가중치 구조는 기본적으로 유지한다.
Capital Model별 세부 benchmark는 충분한 표본을 확보한 뒤 calibration한다.

## Layer 3 — Quant Engine

Case별로 고정된 Quant Core를 계산한다.

Profitable Growth v1:
1. Revenue Growth
2. Operating Profit Growth
3. Margin Trend
4. Cash Economics
5. Capital Efficiency
6. Balance Sheet
7. Dilution
8. Per-share Growth

## Layer 4 — Valuation

Quant Quality와 분리한다.

목적:
- Great Company != Great Stock
- 시장 가격에 이미 얼마나 높은 성장이 반영되어 있는지 판단

추후:
- Forward multiples
- historical band
- peer comparison
- reverse DCF
- Bull / Base / Bear expected return

## Layer 5 — Narrative

정성 평가는 Quant 이후 수행한다.

공통 5문항:
1. Why Growth?
2. Why Continue?
3. Why This Company?
4. What Is Market Missing?
5. What Breaks The Thesis?

Narrative는 Quant 점수를 수정하지 않는다.

## Layer 6 — Tracking

기업별 KPI 1~3개만 저장한다.

예:
STRL
- Organic backlog growth
- E-Infrastructure margin
- Book-to-burn

Tracking KPI는 Core 지표가 아니다.

## Layer 7 — Performance

향후 반드시 측정:
- 3M / 6M / 1Y returns
- Benchmark alpha
- Maximum drawdown
- Grade migration
- Thesis hit / miss
- Narrative upgrade / downgrade accuracy
