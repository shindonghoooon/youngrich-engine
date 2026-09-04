# Youngrich Engine — Project Handoff

> **Project:** 주식으로 파이어 프로젝트
> **Repository:** `shindonghoooon/youngrich-engine`
> **Document Date:** 2026-09-02
> **Status:** Case 1 v1 Frozen / Case 2 v1 Frozen / Persistence Phase 1 checkpointed / Performance Engine Phase 1 stabilized

---

# 0. Authoritative v1 Decisions

This section is the current source of truth. Later Case 2 historical validation notes
explain how the design evolved; any `candidate`, `provisional`, or `not frozen` wording
in those notes is superseded by this section.

Detailed authoritative specifications:

- [Case 2 Quant v1](docs/case2-quant-v1.md)
- [Case 2 Current Trend v1](docs/case2-current-trend-v1.md)
- [Narrative v1](docs/narrative-v1.md)
- [Common Valuation v1](docs/valuation-v1.md)
- [Investment Grade v1](docs/investment-grade-v1.md)
- [Tracking Engine v1 Phase 1](docs/tracking-engine-v1.md)
- [Persistence Phase 1](docs/persistence-v1.md)
- [Performance Engine Phase 1](docs/performance-engine-v1.md)
- [Historical Performance Stress Calibration v0.1](docs/validation/historical-performance-stress-calibration-v0.1.md)

The detailed files own formulas, thresholds, and edge cases. This handoff document owns
the high-level architecture and frozen status; avoid copying new formula variants here.

## Frozen status

```text
Case 1 Profitable Growth Quant v1
→ FROZEN

Case 1 Current Trend Overlay v1
→ FROZEN

Case 2 Emerging / Asymmetric Growth Quant v1
→ FROZEN
```

Do not change existing Case 1 thresholds, weights, or formulas. Frozen logic may be
reopened only after repeated failure across multiple companies or realized-performance
evidence of systematic failure.

## Case 2 Quant v1

| Metric | Weight |
|---|---:|
| Revenue Growth | 30% |
| Gross Profit Growth | 15% |
| Cash Burn Trend | 15% |
| Runway | 15% |
| Dilution | 15% |
| Revenue / Share Growth | 10% |

Supporting observations:

- Gross Margin Trend
- Incremental Operating Margin
- Potential Dilution
- Growth Scope

Guardrail:

```text
Cash Burn X AND Dilution X
→ Quant Grade maximum D
```

Growth Scope:

- `SAME_SCOPE`
- `PRO_FORMA_COMPARABLE`
- `ACQUISITION_INFLUENCED`
- `UNRESOLVED`

## Case 2 Narrative v1

Dimensions:

- Differentiation
- Defensibility
- Adoption
- Penetration / Expansion
- Durability
- Failure Mode

States:

- `PROVEN`
- `STRONG`
- `EMERGING`
- `WEAK`
- `UNRESOLVED`

Narrative is linked to a versioned Thesis Definition and a versioned Tracking KPI set.
It never changes Quant.

## Case 2 Current Trend v1

Signals:

- Revenue Momentum
- Gross Profit Momentum
- Cash Burn Momentum
- Funding / Runway
- Thesis KPI Momentum

Flags:

- `COMMERCIAL_INFLECTION`
- `FUNDING_STRESS`
- `COMMERCIAL_DETERIORATION`

Aggregation:

```text
resolved signals < 4
→ UNRESOLVED

positive >= 4 and negative = 0
→ STRONG_POSITIVE

positive >= 2 and negative >= 2
→ MIXED

positive >= 3 and negative <= 1
→ POSITIVE

negative >= 3 and positive <= 1
→ NEGATIVE

otherwise
→ NEUTRAL
```

Current Trend is a direction classification, not a weighted score.

## Common Valuation v1

- Required Growth / Market-implied Expectations
- Required Return sensitivity: 10%, 15%, 20%; default 15%
- Terminal Stage: `GROWTH`, `TRANSITION`, `MATURE`
- Exit Multiple evidence: company history, comparable companies, and
  business/capital model benchmark
- Conservative / Base / Premium exit ranges
- Expectation Gap
- Bear / Base / Bull
- Downside Severity
- Upside Optionality
- Asymmetry Type
- Valuation Confidence

Valuation assumptions are versioned. A price-only update creates a new valuation output
without mutating the assumption version. Price movement alone must not change exit,
growth, required-return, or terminal-stage assumptions.

## Investment Grade v1

Allowed grades:

```text
A / B / C / D / X / U
```

Use the valuation result as the initial grade. Quant, Current Trend, Narrative, Funding
Stress, Commercial Inflection, Valuation Confidence, and Thesis Breaker are explicit
gates or caps. Do **not** implement a weighted-average Investment Grade.

## Historical look-ahead and price timing

```text
financial_information.available_at <= analysis.as_of
valuation_information.available_at <= analysis.as_of
```

`period_end`, `available_at`, and `as_of` are separate. Historical price snapshots use
the first executable market price after all required information became public. Never
combine a year-end market price with later-released annual results.

## Tracking Schema v0.1

The versioned Pydantic contracts are in `engine/tracking_models.py`:

- `AnalysisSnapshot`
- `QuantSnapshot`
- `MetricResult`
- `CurrentTrendSnapshot`
- `NarrativeSnapshot`
- `ThesisDefinition`
- `TrackingKPIDefinition`
- `TrackingKPIObservation`
- `ThesisStatusSnapshot`
- `ValuationSnapshot`
- `InvestmentGradeSnapshot`
- `SnapshotDiff`
- `PerformanceSnapshot`

Invariants:

- Analysis snapshots are immutable historical records and are never overwritten.
- Thesis definitions, KPI sets, and valuation assumptions are versioned.
- Narrative KPI sets cannot silently change between periods.
- Price-only changes preserve the valuation assumption version.
- `available_at > as_of` fails validation.
- `unresolved` never silently becomes zero.
- Models support Case 1 and Case 2 without company-specific fields.

This stabilization does not implement dashboard/frontend/PWA, real-time price APIs,
alerts, scheduled ingestion, full database persistence, Case 3+, or new investment metrics.

---

# 1. Project Goal

이 프로젝트의 최종 목적은 단순히 위험한 종목을 걸러내는 것이 아니다.

> **장기적으로 큰 주가 상승을 만들어낼 수 있는 실제 투자 후보를 체계적으로 발굴하고 추적하는 투자 분석 엔진을 만든다.**

특히 다음 세 가지 유형을 서로 다른 논리로 분석한다.

1. 흑자 성장주
2. 초기 / 적자 / 비대칭 성장주
3. 대형 우량주 및 저평가주

향후 Cyclical, Compounder, Asset/Special Situation 등으로 확장한다.

핵심 철학은:

> **좋은 회사와 좋은 주식은 다르다.**

따라서 기업의 질과 현재 주가는 반드시 분리해서 분석한다.

---

# 2. System Architecture

전체 구조:

```text
Stock
  ↓
Case Router
  ↓
Capital Model
  ↓
Case-specific Quant Engine
  ↓
Quant Quality
  ↓
Current Trend
  ↓
Valuation / Asymmetry
  ↓
Narrative / Expectation Gap / Risk
  ↓
Tracking KPI
  ↓
Investment Grade
  ↓
Realized Performance Tracking
```

중요:

```text
Quant Grade ≠ Investment Grade
```

Quant는 기업 자체의 재무적 상태를 평가한다.

현재 주가는 Quant에 절대 반영하지 않는다.

가격은 이후 Valuation / Asymmetry Layer에서 반영한다.

예:

```text
Quant A + 극단적 고평가
→ Investment Grade C 가능

Quant B/C + 강한 Narrative + 큰 Asymmetry
→ 좋은 투자 후보 가능
```

---

# 3. Core Design Principles

## 3.1 Case는 회사의 영구적인 정체성이 아니다

Case는:

> **현재 시점에서 그 회사를 분석할 때 가장 중요한 경제적 구조 / 투자 Thesis**

를 의미한다.

기업은 시간이 지나면서 Case가 변경될 수 있다.

예:

```text
Case 2 Emerging Growth
        ↓
흑자 전환
        ↓
Case 1 Profitable Growth
        ↓
성장 둔화
        ↓
Case 4/5
```

---

## 3.2 회사 특이사항 때문에 Common Quant Metric을 추가하지 않는다

특정 기업 하나 때문에 Core Metric을 추가하거나 공식을 수정하지 않는다.

수정 조건은:

> 동일한 왜곡이 여러 회사에서 반복적으로 발생할 때.

Company-specific 문제는:

- Narrative
- Supporting Signal
- Normalization
- Tracking KPI

등에서 처리한다.

---

## 3.3 Narrative는 Quant Grade를 바꾸지 않는다

기술력이 강하다는 이유로 좋지 않은 Quant 결과를 A로 바꾸지 않는다.

```text
Quant
= 실제 숫자로 확인되는 사실

Narrative
= 그 숫자가 앞으로 왜 지속/가속될 수 있는지 설명
```

둘은 최종 Investment Grade 단계에서 결합한다.

---

## 3.4 Capital Model은 Case가 아니다

현재 Capital Model 후보:

```text
asset_light
manufacturing
capital_intensive
project_based
rd_ip_driven
```

Capital Model은:

- 지표를 새로 추가하지 않는다.
- 해당 지표의 의미나 benchmark를 해석하는 역할이다.

Capital Model별 threshold calibration은 아직 미완료.

---

## 3.5 Structured Data가 Source of Truth

최종적으로:

```text
Financial Data / DB
→ Metrics
→ Quant Snapshot
→ Narrative
→ Tracking
→ Report / Dashboard
```

구조로 간다.

보고서가 Source of Truth가 되어서는 안 된다.

---

# 4. Cases

현재 Case 구조:

```text
Case 1
Profitable Growth

Case 2
Emerging / Asymmetric Growth
(기존 코드명 Loss-making Growth일 수 있음)

Case 3
Cyclical / Mean Reversion

Case 4
Quality Compounder

Case 5
Large-cap Value / Mature Quality

Case 6
Asset / Special Situation
```

Case 2 이름 및 기존 enum migration은 아직 확정하지 않는다.

---

# 5. Case 1 — Profitable Growth

## STATUS

**FROZEN v1**

다수 기업 검증까지 완료.

반복적 오류 또는 실제 투자 성과 검증에서 문제가 나타나기 전에는 재설계하지 않는다.

---

# 6. Case 1 Definition

이미 흑자를 내면서 성장하는 기업.

핵심 질문:

> 매출 성장이 실제 이익 성장과 자본 효율로 연결되고 있으며 그 성장의 과실이 주주에게 돌아오고 있는가?

---

# 7. Case 1 Quant Core 8

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

Grade Score:

```text
A = 4
B = 3
C = 2
D = 1
X = 0
```

Quant Grade:

```text
A >= 3.50
B >= 3.00
C >= 2.40
D >= 1.80
X < 1.80
```

---

# 8. Case 1 Thresholds

## Revenue Growth

3Y CAGR:

```text
A >= 25%
B 15–25%
C 8–15%
D 0–8%
X < 0%
```

## Operating Profit Growth

3Y CAGR:

```text
A >= 30%
B 18–30%
C 8–18%
D 0–8%
X < 0%
```

## Margin Trend

3Y Operating Margin Change:

```text
A >= +3%p
B +1 ~ +3%p
C -1 ~ +1%p
D -3 ~ -1%p
X < -3%p
```

## Capital Efficiency — ROIC

```text
A >= 20%
B 12–20%
C 8–12%
D 5–8%
X < 5%
```

## Balance Sheet

Net Debt / EBITDA:

```text
Net Cash or <=1x : A
1–2x              : B
2–3x              : C
3–4x              : D
>4x                : X
```

## Dilution

3Y Diluted Share CAGR:

```text
<=0%   A
0–2%   B
2–5%   C
5–10%  D
>10%   X
```

## Per-share Growth

Diluted EPS CAGR:

```text
>=25%   A
15–25%  B
8–15%   C
0–8%    D
<0%     X
```

---

# 9. Case 1 Cash Economics v1

Primary Metric:

```text
3Y cumulative CFO
------------------
3Y cumulative Consolidated Net Income
```

Threshold:

```text
>=1.00       A
0.80–1.00    B
0.60–0.80    C
0.40–0.60    D
<0.40        X
```

Important distinction:

```text
net_income_consolidated
→ CFO conversion용

net_income_common
→ shareholder-level supporting field
```

CAPEX Intensity:

```text
Cumulative CAPEX / Cumulative CFO
```

은 Supporting Reinvestment Tag이다.

CAPEX가 높다는 이유만으로 Cash Economics grade를 낮추지 않는다.

---

# 10. Case 1 ROIC v1

Standardized formula:

```text
Effective Tax Rate
= Tax Expense / Pretax Income

NOPAT
= Operating Income × (1 - Effective Tax Rate)

Invested Capital
= Total Debt + Total Equity - Cash

Average IC
= (Beginning IC + Ending IC) / 2

ROIC
= NOPAT / Average IC
```

Guardrail:

```text
Pretax Income <= 0
→ unresolved

Tax Rate outside 0–40%
→ unresolved
```

현재 하지 않는 조정:

- excess cash
- goodwill
- lease adjustment
- R&D capitalization
- negative working capital
- sector-specific adjustment

---

# 11. Financial Input / Normalization Layer

Raw official financial data:

```text
SEC / DART / Official IR
        ↓
Pydantic validation
        ↓
Unit normalization
        ↓
Metrics
        ↓
Case Engine
```

Period key에는 반드시:

```text
fiscal_year
fiscal_period_end
```

을 저장한다.

비 12월 결산 기업 대응을 위해 CAGR 등은 `fiscal_period_end` 기준으로 정렬한다.

기본 annual fields:

```text
Revenue
Operating Income
Pretax Income
Tax Expense

Consolidated Net Income
Common Net Income

CFO
CAPEX

Cash
Total Debt
Total Equity

Diluted Shares
Diluted EPS

EBITDA
Source Metadata
```

Core metric이 unresolved이면 임의로 점수를 만들지 않는다.

---

# 12. Case 1 Annual Validation

검증 기업:

| Company | Capital Model | Score | Grade |
|---|---|---:|---|
| Samyang Foods | manufacturing | 4.00 | A |
| Eli Lilly | rd_ip_driven | 3.80 | A |
| STRL | project_based | 3.65 | A |
| LS ELECTRIC | manufacturing | 3.15 | B |
| Oracle | capital_intensive | 2.70 | C |

Case 1 Annual Engine은 이 결과로 v1 Frozen.

---

# 13. Case 1 Current Trend Overlay v1

## STATUS

**FROZEN v1**

Annual Quant를 수정하지 않는다.

```text
Annual Quant
= 증명된 장기 Quality

Current Trend
= 최근 사업 방향
```

Sub-signals:

```text
1 Revenue Growth
2 Operating Profit Growth
3 Margin Trend
4 Cash Economics
5 Balance Sheet
```

현재 제외:

- Current ROIC
- Current Dilution
- Current Per-share

Quarterly noise가 너무 크기 때문.

---

# 14. Current Trend Aggregation

Resolved signals < 3:

```text
unresolved
```

그 외:

```text
positive >=3 and positive > negative
→ positive

negative >=3 and negative > positive
→ negative

positive >=2 and negative >=2
→ mixed

else
→ neutral
```

Current Trend는 score가 아니다.

---

# 15. Current Cash Overlay Calibration

Annual CFO Conversion 대비 Current Conversion:

```text
>= Annual × 1.10
→ positive

within ±10%
→ neutral

< Annual × 0.90 AND Current >= 1.00x
→ neutral
  "relative deterioration,
   absolute conversion remains healthy"

< Annual × 0.90 AND Current < 1.00x
→ negative
```

---

# 16. TTM EBITDA

단순 quarterly annualization 금지.

공식 bridge:

```text
TTM EBITDA
=
Latest Annual EBITDA
+ Current YTD EBITDA
- Prior Comparable YTD EBITDA
```

official/reproducible EBITDA bridge가 없으면 unresolved.

---

# 17. Look-ahead Rule

분석 시점 `as_of` 이후 공개된 데이터는 절대 사용하지 않는다.

```text
source filing date <= as_of
period end <= as_of
```

Historical backtest에서도 동일.

---

# 18. Case 2 — Emerging / Asymmetric Growth

## STATUS

**FROZEN v1**

Case 2의 operative v1 구조는 Section 0에 고정한다. 아래 historical discussion은
설계 선택의 배경이며 현재 규칙을 변경하지 않는다.

초기에는 `Loss-making Growth`라는 이름으로 설계했으나 현재 철학은 더 좁고 명확하다.

Case 2는:

> **작지만 실제 상용 매출이 발생하기 시작했고, 시장 침투 과정에서 높은 성장 가능성을 가지며 성공 시 현재 기업가치 대비 큰 비대칭적 upside가 존재하는 기업**

을 찾는 Case다.

Case 2의 목적은 단순 적자기업 분석이 아니다.

---

# 19. Case 2 Core Philosophy

Case 1처럼 완성된 기업 Quality를 평가하려고 하지 않는다.

핵심 질문:

```text
1. 실제 고객 수요가 발생하고 있는가?
2. 매출이 빠르게 증가하고 있는가?
3. 돈 떨어지기 전에 살아남을 수 있는가?
4. 희석만으로 성장하는 것은 아닌가?
5. 기술/제품 경쟁력이 성장 지속성을 만들 수 있는가?
6. 성공하면 현재 시총 대비 upside가 큰가?
```

구조:

```text
Quant Screening
      +
Narrative Conviction
      +
Asymmetric Payoff
      ↓
Investment Grade
```

Case 2에서는 Narrative와 Asymmetry의 중요도가 Case 1보다 크다.

---

# 20. Case 2 Eligibility — Historical Design Context

기본적으로:

```text
Core Business Revenue > 0

Gross Profit > 0

Operating Income < 0

Core Business Revenue Representative = YES
```

또한 실제 상용 고객이 존재해야 한다.

기업 상태:

```text
Pre-commercial
→ Case 2 Core 대상 제외

Early Commercial
→ Edge / Watch

Scaling Commercial
→ Case 2 Primary
```

Revenue Growth에 현재 hard cutoff는 두지 않는다.

그러나 Case 2 철학상:

> 매출이 거의 없는 기술 스토리 기업보다 실제 매출이 빠르게 증가하기 시작한 기업을 선호한다.

---

# 21. Case 2 Quant Design History (Superseded)

기존에는 8 Core를 실험했다.

이전 실험안:

```text
Revenue Growth
Gross Profit Growth
Gross Margin Trend
Incremental Operating Margin
Cash Burn Trend
Runway
Dilution
Gross Profit / Share Growth
```

Historical Winner/Failure validation 결과:

- 실패기업 filtering에는 강함
- 그러나 NET / CRWD / MDB / TSLA 등 초기 승자의 공격적 성장투자를 과도하게 penalty하는 문제가 확인됨
- 특히 Incremental Operating Margin 20%가 초기 성장주를 지나치게 누를 가능성이 있음
- GP/share는 Dilution과 중복성이 큼

따라서 이 8 Core 실험안은 폐기되었고 현재 Frozen 구조가 아니다. Section 0의
6 Core가 frozen v1이다.

---

# 22. Case 2 Simplified Quant v1 — Frozen

Frozen v1 구조:

| Area | Metric | Weight |
|---|---|---:|
| Growth | **Revenue Growth** | **30%** |
| Growth Quality | Gross Profit Growth | 15% |
| Survival | Cash Burn Trend | 15% |
| Survival | Runway | 15% |
| Shareholder | Dilution | 15% |
| Shareholder Growth | **Revenue / Share Growth** | **10%** |

Total:

```text
100%
```

이 구조의 목적:

```text
Demand
→ Revenue / GP

Survival
→ Burn / Runway

Shareholder Economics
→ Dilution / Revenue per Share
```

Case 2 Quant를 지나치게 복잡하게 만들지 않는다.

---

# 23. Why Revenue Growth Is Central in Case 2

Case 2에서는 매출 성장을 가장 중요하게 본다.

이유:

> Narrative가 실제 상업화로 바뀌기 시작했다는 가장 직접적인 증거이기 때문.

특히 기술 기업이라도:

```text
기술 좋음
TAM 큼
매출 없음
```

보다:

```text
기술 우위
+
실제 고객 adoption
+
빠른 Revenue Growth
```

을 선호한다.

---

# 24. Revenue per Share

Case 2에서 희석 문제가 중요하기 때문에:

```text
Revenue per Share
= Revenue / Diluted Shares
```

를 사용한다.

목적:

```text
Company Revenue +100%
Shares +5%
→ shareholder growth 강함

Company Revenue +100%
Shares +70%
→ company는 성장하지만
   shareholder economics는 약함
```

즉:

> 기업 전체 성장과 주주 몫의 성장을 구분한다.

---

# 25. Gross Margin

Gross Margin은 Frozen v1에서 Supporting Signal이다.

이유:

업종별 경제 구조 차이가 너무 크다.

예:

```text
SaaS
70% GM 가능

Manufacturing / Deep Tech
20~40% GM 가능

Marketplace / Commerce
Business Mix 때문에 GM 급변 가능
```

Gross Margin이 증가한다고 경제적 해자가 강한 것도 아니다.

따라서:

```text
Gross Margin
→ unit economics / business mix supporting signal

Technology Moat
→ Narrative에서 별도 평가
```

Gross Margin의 절대 수준으로 다른 업종을 비교하지 않는다.

---

# 26. Incremental Operating Margin

공식:

```text
Δ Operating Income
------------------
Δ Revenue
```

은 유용한 Supporting Signal이다.

단:

```text
ΔRevenue <= 0
→ Scaling failure / X-type signal
```

을 적용해야 한다.

Frozen v1에서는 Core가 아닌 Supporting Signal이다.

이유:

NET / CRWD / MDB 등 초기 고성장주는:

```text
Revenue ↑↑
GP ↑↑

but

R&D / Sales investment ↑↑
→ Operating Loss 확대
```

가 가능하다.

이를 단순히 나쁜 economics로 해석해서는 안 된다.

---

# 27. Case 2 Cash Burn Normalization

단순:

```text
CFO - PP&E
```

만으로 계산하지 않는다.

Growth CAPEX 후보:

```text
PP&E purchases

+ capitalized internal-use software

+ capitalized product/software development
```

제외:

```text
Acquisition purchase price
Marketable securities purchases
Financial investments
```

Case 2 FCF candidate:

```text
FCF
= CFO - Growth CAPEX
```

Burn:

```text
Cash Burn
= max(0, -FCF)
```

이 historical normalization section은 threshold를 새로 정의하지 않는다. Frozen
v1 구조는 Section 0을 따른다.

---

# 28. Runway

Candidate definition:

```text
Liquidity
=
Cash
+ unrestricted short-term marketable securities
```

```text
Runway
=
Liquidity / Annualized Cash Burn
```

과거 실험 threshold (operative v1 specification 아님):

```text
FCF positive or >=36 months → A
24–36 months               → B
12–24 months               → C
6–12 months                → D
<6 months                  → X
```

이 threshold는 현재 검증용일 뿐 Frozen 아님.

---

# 29. Dilution Normalization Issue

Case 2 기업은 IPO/SPAC/Direct Listing 직후가 많다.

따라서:

```text
IPO
SPAC recapitalization
Direct Listing
Reverse recapitalization
```

을 가로지르는 share-count change를 일반적인 Dilution으로 사용하면 안 된다.

원칙:

> Comparable post-listing period만 Dilution 계산에 사용한다.

비교 가능한 기간이 없으면:

```text
unresolved
```

로 처리한다.

X로 처리하지 않는다.

비교 불가능한 기간은 Tracking Schema v0.1에서 first-class `unresolved`로 보존한다.

---

# 30. Case 2 Narrative

Case 2에서 Narrative는 매우 중요하다.

하지만 단순 Story가 아니라:

> **왜 현재 Revenue Growth가 지속될 수 있는가?**

를 설명해야 한다.

핵심 구조:

```text
Technology Moat
      ↓
Customer Adoption
      ↓
Market Penetration
      ↓
Revenue Growth
```

---

# 31. Narrative Framework Design History

## Technology Moat

```text
기술이 기존 방식보다 실제로 우월한가?

경쟁사가 복제하기 어려운가?

IP / Data / Process /
Regulatory / Network barrier가 있는가?
```

## Adoption

```text
실제 고객이 증가하는가?

Pilot → Commercial contract가 되는가?

Repeated / Expanded contract가 발생하는가?
```

## Penetration

```text
현재 시장 침투율이 낮은가?

점유율을 더 가져갈 공간이 있는가?
```

## Competitive Position

```text
왜 경쟁사 대신 이 회사인가?
```

## Failure Mode

```text
Technology Failure
Funding Failure
Competition
Commercialization Delay
Execution Failure
```

---

# 32. TAM

TAM은 Quant Metric이 아니다.

TAM은 과장되기 쉽기 때문에:

```text
Large
Medium
Limited
```

정도의 Narrative / Asymmetry context로 사용한다.

Hard eligibility 또는 Quant score로 사용하지 않는다.

---

# 33. Narrative → Numeric Tracking KPI

향후 1장짜리 종목 보고서를 만들 때 반드시 구현할 중요 기능.

Narrative를 글로만 저장하지 않는다.

각 Narrative Thesis를:

> **실제 숫자로 검증 가능한 Tracking KPI**

로 변환한다.

예:

## Technology Moat

```text
Performance improvement
Cost advantage
Yield
Processing speed
Patents
Technical milestone
```

## Adoption

```text
Customer Count
New Customers
Paid Conversion
Repeat Contract
Expansion Contract
```

## Commercialization

```text
Backlog
Contract Value
Production Capacity
Shipments
Revenue Conversion
```

## Market Penetration

```text
Market Share
Installed Base
Units Shipped
Geographical Expansion
Customer Segment Expansion
```

## Pricing Power

```text
ASP
Price Increase
Demand Retention
```

Narrative tracking concept:

```text
Narrative
   ↓
Tracking KPI
   ↓
Quarterly Update
   ↓
Thesis Confirming / Weakening / Broken
```

Tracking Schema v0.1은 이 연결을 위한 versioned Thesis/KPI domain contract를 제공한다.

---

# 34. Future One-page Report Concept

예시:

```text
Company: XXX

Case
Emerging / Asymmetric Growth

Quant
C

Current Trend
Positive

Narrative
Strong

--------------------------------

Core Tracking KPI

Revenue Growth       +65% ↑
Customers            120 → 185
Backlog              $300M → $520M
Market Share         2.1% → 3.4%
Gross Margin         28% → 32%

--------------------------------

Technology Moat
Confirming

Adoption
Confirming

Penetration
Confirming

Funding Risk
Watch

--------------------------------

Valuation / Asymmetry

Current Market Cap
Base Success
Bull Success
Failure Scenario

--------------------------------

Investment Grade
XXX
```

보고서에는 “무엇을 다음 분기에 확인할 것인가?”가 반드시 포함되어야 한다.

---

# 35. Case 2 Asymmetry Layer

아직 구현 전.

Case 2에서는 전통적인 PER/PBR보다 성공 시 기업가치 시나리오가 더 중요할 수 있다.

예:

```text
Current Market Cap
$500M

Failure Scenario
$100M

Base Success
$1.5B

Bull Success
$5B
```

그리고:

```text
Downside
vs
Base Upside
vs
Bull Upside
```

를 분석한다.

Quant와 Asymmetry를 섞지 않는다.

---

# 36. Case 2 Validation Basket

## Current Core

```text
IONQ
LPTH
TEM
EROC
```

## Historical Winners

```text
PLTR
SHOP
NET
CRWD
ROKU
TSLA
```

## Later Success / Borderline

```text
MDB
```

## Mediocre

```text
FSLY
```

## Historical Failure

```text
SKLZ
VLDR
```

## Edge / Eligibility Tests

```text
USAR
JOBY
```

---

# 37. Why Historical Winners Were Added

초기 basket은 실패/정체 기업 비중이 높았다.

그 결과 엔진이:

> “나쁜 회사를 거르는 능력”

은 좋아 보였으나:

> “초기 대박주를 놓치지 않는 능력”

검증이 부족했다.

Historical Winners를 추가하면서 다음 문제를 발견했다.

NET / CRWD / MDB / TSLA 등의 초기 단계에서는:

```text
Revenue ↑↑
Gross Profit ↑↑

BUT

R&D / Sales / CAPEX ↑↑
Operating Loss 확대
```

가 충분히 가능하다.

따라서 Case 2를 Case 1처럼 Profitability Quality Engine으로 만드는 것은 잘못된 방향일 수 있다.

---

# 38. Historical Backtest Rule

Historical Winner를 사용할 때 미래 데이터를 절대 사용하지 않는다.

예:

```text
PLTR @ FY2021

사용 가능:
FY2019
FY2020
FY2021
당시 공개된 정보

사용 금지:
FY2022+
현재 주가
현재 시총
현재 성공 여부
```

이는 survivorship / hindsight bias 방지를 위해 필수.

---

# 39. Important Lessons From Validation

### PLTR

초기 단계에서도:

```text
Revenue ↑↑
GP ↑↑
Margins 개선
Cash economics 개선
```

이 나타나 Strong Case 2 패턴.

### SKLZ

```text
Revenue ↑↑
GP ↑↑

BUT

Loss ↑↑
Cash Burn ↑↑
Dilution ↑
```

즉:

> Revenue Growth alone is not enough.

### FSLY

성장은 있었지만:

```text
GP Growth 둔화
GM 악화
Loss 확대
Burn 확대
```

가 나타남.

### NET / CRWD / MDB

좋은 초기기업도 공격적 성장투자로 영업손실이 확대될 수 있다.

따라서:

> Operating Loss Expansion alone ≠ bad growth.

### LPTH

Annual historical numbers는 매우 약하지만 최신 사업이 급격하게 inflection할 수 있다.

따라서 Case 2에도 향후:

```text
Annual/Base Quant
+
Current Trend Overlay
```

구조가 필요할 가능성이 매우 높다.

Case 2 Current Trend v1의 signal/flag/aggregation domain은 Section 0에 frozen되어 있다.
실제 계산 엔진은 이 documentation/domain stabilization 범위에서 구현하지 않는다.

---

# 40. Case 2 Grade Interpretation — Historical Lesson

Historical validation 과정에서:

```text
Quant A/B
→ 이미 숫자로도 상당히 강한 Emerging Company

Quant C
→ 반드시 탈락이 아님
```

이라는 점이 확인됐다.

특히 Case 2 C는 향후:

> **Asymmetric Candidate**

의 의미를 가질 가능성이 있다.

즉:

```text
Quant C
+
Strong Technology Moat
+
Strong Adoption
+
Low Penetration
+
Large Asymmetry
```

이면 매우 좋은 투자 후보가 될 수 있다.

Investment Grade는 Section 0의 valuation-initial, gate/cap 구조로 별도 관리하며
Quant와 가중평균하지 않는다.

---

# 41. Router Issues / Deferred Work

Case Router는 아직 calibration 완료가 아니다.

과거 문제:

Quality Compounder condition 및 fallback 논리.

현재 원칙:

> Frozen Case 1/2 domain을 이유로 Router를 성급하게 확장하지 않는다.

특히:

```text
Profitable Growth
vs
Quality Compounder
```

경계도 향후 다시 검증한다.

---

# 42. Valuation

Common Valuation v1 domain contract는 Section 0과 `engine/tracking_models.py`에
정의되어 있다. Pure calculation은 `engine/valuation_engine.py`가 담당하며 market
price/market cap을 입력으로만 받는다. 실시간 가격 조회는 구현하지 않는다.

Valuation은 Quant와 분리한다.

Case별 Valuation 방식이 다를 수 있다.

예:

```text
Case 1
PER / EV/EBIT / FCF / Growth-adjusted multiples

Case 2
Current Market Cap vs Future Success Scenarios

Case 3
Mid-cycle earnings

Case 5
Normalized earnings / FCF / assets
```

Required Growth, required-return sensitivity, terminal stage, exit-range evidence,
Expectation Gap, Bear/Base/Bull, downside/upside, asymmetry, confidence와 versioned
assumptions가 공통 v1 구조다.

---

# 43. Investment Grade

Investment Grade v1 domain contract와 pure grade calculation은 구현되어 있다.
`engine/investment_grade_engine.py`는 upstream Quant/Current/Narrative/Valuation 결과만
소비하며 이를 내부에서 다시 계산하지 않는다.

장기 구조:

```text
Quant Quality
+
Current Trend
+
Valuation / Asymmetry
+
Narrative
+
Expectation Gap
+
Risk
+
Tracking Evidence
        ↓
Investment Grade
```

Investment Grade는 `A/B/C/D/X/U`를 사용한다. Valuation 결과를 initial grade로
사용하고 다른 layer는 명시적 gate/cap으로만 반영한다. weighted-average 방식은
금지한다.

---

# 44. Tracking & Realized Performance

최종적으로 모든 분석은 성과 검증으로 이어져야 한다.

향후 저장 대상:

```text
Quant Grade at analysis date
Investment Grade
Price at analysis
1M return
3M return
6M return
1Y return
Max Drawdown
Thesis status
```

이를 이용해서:

```text
어떤 Case에서
어떤 Quant 패턴이
실제로 좋은 수익률로 연결됐는가
```

를 검증한다.

장기적으로 threshold와 weighting은 이 데이터로 calibration한다.

---

# 45. Current Repo / Implementation Status

Current source of truth:

```text
youngrich-engine
```

Old `youngrich` repo는 Legacy / Prototype 취급.

Case 1:

```text
Annual Quant Engine
→ Frozen v1

Current Trend Overlay
→ Frozen v1
```

Case 2:

```text
Emerging / Asymmetric Growth Quant
→ Frozen v1 specification + pure calculation engine

Narrative / Current Trend / Valuation / Investment Grade
→ frozen v1 contracts + deterministic pure calculation engines
```

Tracking:

```text
Tracking Schema v0.1
→ immutable/versioned Pydantic domain models implemented

Tracking Engine v1 Phase 1
→ PriceSnapshot, SnapshotDiff, Thesis Tracking,
  valuation Entry Zone, and grade-change attribution implemented

Persistence Phase 1
→ SQLAlchemy/Alembic append-only schema, explicit mappers, and repositories implemented

Performance Engine Phase 1
→ adjusted-price horizons, MDD completeness, comparable benchmark alpha, persistence,
  and cohort analytics implemented

Providers / dashboard / alerts
→ deferred
```

관련 주요 commits:

```text
102168f
Case1 cross-company annual validation

d64f72a
Current Trend follow-up

7ace418
Case1 Current Trend Overlay v1 freeze

b34223f
Case2 calculation engines + five-company golden validation

9566d9f
Price-aware Tracking Engine + thesis engine checkpoint

5f9d341
Immutable investment persistence layer checkpoint
```

당시:

```text
72 tests passed
working tree clean
origin/main pushed
```

---

# 46. Known Financial Normalization TODO

향후 해결:

```text
EBITDA field-level provenance

Supplied vs reconstructed EBITDA

Total Debt scope

Lease liability consistency

Case2 Growth CAPEX normalization

IPO/SPAC share-count comparability
```

이 문제들은 Core Metric 추가 사유가 아니다.

Normalization layer 문제로 해결한다.

---

# 47. Collaboration Workflow

역할 분리:

## ChatGPT Design Session

담당:

```text
Investment philosophy
Architecture
Metric design
Threshold design
Validation
Historical backtest logic
Review
Cowork instructions
```

## Cowork / Codex

담당:

```text
Repo edits
Implementation
Tests
Git commits
Push
Code-level validation
```

Workflow:

```text
ChatGPT에서 설계
      ↓
구체적인 Cowork 지시문 작성
      ↓
User가 Cowork 실행
      ↓
결과 / diff / test 결과 전달
      ↓
ChatGPT review
      ↓
다음 설계
```

중요:

> Cowork가 임의로 투자 논리를 변경하게 하지 않는다.

구현은 설계를 따라야 한다.

---

# 48. Project Leadership Rule

사용자 아이디어라고 해서 무조건 동의하지 않는다.

프로젝트 구조와 충돌하거나 overfitting 위험이 있으면 적극적으로 문제를 제기한다.

특히 피해야 할 것:

```text
특정 종목 하나 때문에 Core 추가

과거 승자를 A로 만들기 위한 threshold 조정

Narrative로 Quant 결과 덮기

TAM을 숫자처럼 사용

현재 가격을 Quant에 넣기

Future knowledge를 Historical test에 사용
```

---

# 49. Current Exact Position

현재 프로젝트는:

```text
Case 1
██████████ 100%
Frozen

Case 1 Current Trend
██████████ 100%
Frozen

Case 2 Quant v1
██████████ 100%
Frozen v1 + pure calculation engine

Case 2 Narrative
██████████ 100%
v1 domain contract + categorical gate engine

Case 2 Current Trend
██████████ 100%
v1 signal/flag/aggregation contract + pure engine

Case 2 Asymmetry
██████████ 100%
Common Valuation v1 required-growth engine

Valuation
██████████ 100%
Case 1 PE and Case 2 terminal-stage calculations implemented

Investment Grade
██████████ 100%
Global precedence and deterministic gate/cap engine implemented

Tracking Schema
██████████ 100%
Immutable/versioned domain contract implemented

Tracking Engine v1 Phase 1
██████████ 100%
Price, snapshot diff, thesis status, entry zone, and attribution implemented

Persistence Phase 1
██████████ 100%
Append-only SQLAlchemy schema, Alembic baseline, mappers, and repositories implemented

Performance Engine Phase 1
██████████ 100%
Adjusted-price performance, MDD coverage, comparable benchmark alpha, immutable
evaluations, and cohorts implemented

Providers / dashboard / alerts
→ deferred
```

---

# 50. Historical Case 2 Freeze Step — Completed

아래 historical-basket 재검증 단계는 Case 2 Quant v1 freeze 과정에서 완료된
설계 기록이다. 현재 next step이 아니다.

우선 현재 Simplified Candidate:

```text
Revenue Growth           30%
Gross Profit Growth      15%
Cash Burn Trend          15%
Runway                   15%
Dilution                 15%
Revenue / Share Growth   10%
```

를 Historical Basket에 다시 적용한다.

검증 질문:

```text
1. Historical Winners를 지나치게 많이 놓치는가?

2. SKLZ / FSLY / VLDR 같은 약한 성장주를
   여전히 낮게 평가하는가?

3. Revenue Growth를 중심으로 올렸을 때
   Story stock이 너무 쉽게 살아나는가?

4. Dilution + Revenue/share가
   실제 shareholder economics를 잘 구분하는가?

5. SaaS / Deep Tech / Manufacturing 등
   다른 Business Model에서도 작동하는가?
```

이 검증 결과를 반영해:

```text
Case 2 Quant v1 Frozen
```

로 간다.

---

# 51. Post-Freeze Roadmap

Domain stabilization 이후의 구현 순서:

```text
1. Case 2 Narrative Framework

2. Historical Winner Narrative Backtest

3. Technology Moat / Adoption /
   Penetration 평가 기준

4. Case 2 Current Trend

5. Asymmetry / Valuation

6. One-page Report

7. Narrative → Tracking KPI Engine

8. Investment Grade

9. Automated Stock Tracking
```

---

# 52. Final Project Philosophy

Case 1:

> **이미 좋은 기업이 계속 좋은지 확인한다.**

Case 2:

> **아직 완성되지 않았지만 실제 시장을 빠르게 먹기 시작한 회사를, 망하기 전에 발견한다.**

Case 3+:

> 각 경제 구조에 맞는 별도 논리를 사용한다.

그리고 모든 Case에서 최종적으로 묻는 질문은 같다.

> **“지금 이 가격에서 이 회사의 미래를 사는 것이 기대수익 대비 좋은 투자냐?”**

Quant는 그 질문에 답하기 위한 하나의 도구이지 최종 답 자체가 아니다.
