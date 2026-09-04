# Case 2 Golden Validation — 2026-09-01

Status: VALIDATION — COMPLETE

Authoritative for Results: YES

Authoritative for Investment Rules: NO

Outcome-aware: NO

Unbiased Backtest: NO

Last Updated: 2026-09-04

Validation fixture; not investment advice.

Analysis snapshot: 2026-09-01 16:00 US Eastern (regular-session close)
Logic under test: frozen Case 2 Quant, Narrative Gate, Current Trend, Common Valuation, and Investment Grade v1

This validation does not fetch data at test time and does not change frozen policy. The JSON fixtures are manually curated normalized inputs. Amounts are USD thousands unless stated otherwise. A fixture section is one provenance envelope: its `source_id` resolves to source, source date and `available_at`; each period retains `fiscal_period_end`; the JSON key/value is the retrieved normalized field/value; and `normalization_note` records the transformation. Null means unresolved, never zero.

## Overall matrix

| Company | Quant | Current | Narrative Gate | Expectation Gap | Initial IG | Final IG | Validation |
|---|---|---|---|---|---|---|---|
| TEM | 3.25 / B | POSITIVE | CONFIRMED | OVERLAP | B | B | PASS |
| IONQ | 2.80 / D (raw C, funding cap) | MIXED + Funding Stress | QUALIFIED | NEGATIVE | C | C | PASS; prior IG difference classified MANUAL_CALC_ERROR |
| ONDS | 2.95 / C | MIXED + Funding Stress | DEVELOPING | NEGATIVE | C | C | PASS; prior IG difference classified MANUAL_CALC_ERROR |
| LPTH | 0.85 / X | POSITIVE + Commercial Inflection | QUALIFIED | NEGATIVE | C | C | PASS |
| EROC | UNRESOLVED (30% coverage) | NEUTRAL | DEVELOPING | NEGATIVE / confidence UNRESOLVED | U | U | PASS; prior Current difference classified MANUAL_CALC_ERROR |

“PASS” means the independent reference arithmetic and every production output agree. It does not mean the company is attractive. Exit multiples, plausible growth and dilution are versioned `validation_case2_2026_09_v1` mechanics inputs, not frozen company fair-value assumptions.

## Independent-reference method

The golden test reimplements these calculations without importing production policy helpers:

- two-year revenue and gross-profit CAGR;
- `FCF = CFO - normalized Growth CAPEX`, burn change, runway, actual-share dilution and revenue/share growth;
- the six frozen weights, raw score, coverage, grade thresholds and Cash Burn X + Dilution X cap;
- five current signals, acceleration, resolved counts, overall direction, Funding Stress, Commercial Inflection and Commercial Deterioration;
- required future equity value, future EV, future revenue and required CAGR for all three exit bands;
- initial Investment Grade and every narrative, Quant, Current, stress and confidence cap in sequence.

Floating-point values use numeric tolerance. Categorical values require exact equality.

## TEM

### Source snapshot

- Annual: [2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1717115/000119312526066961/tem-20251231.htm), filed 2026-02-24.
- Current: [2026 Q2 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1717115/000119312526326090/tem-20260630.htm), available 2026-07-30.
- Price: [historical regular-session prices](https://www.historicalstockprice.com/tem-historical-stock-prices/), 2026-09-01 close $62.27.

### Normalized inputs

- Revenue 2023/2024/2025: 531,822 / 693,398 / 1,271,789; GP: 286,175 / 381,113 / 797,897.
- 2024/2025 normalized FCF: -211,166 / -245,355. Latest liquidity: 754,998.
- Actual shares 2024/2025: 162,120,761 / 178,279,217.
- H1 revenue: 730,602 vs 570,372; GP: 468,539 vs 350,242; FCF: -101,961 vs -74,343.
- Current liquidity: 815,991; comparable filing-cover shares: 180,434,756 vs 173,727,558.
- Growth Scope is ACQUISITION_INFLUENCED because Ambry/Paige materially changed reported scope.

### Engine output and independent reference

- Revenue CAGR 54.64% A; GP CAGR 66.98% A; burn change +16.19% D; runway 36.93 months A; dilution 9.97% C; revenue/share +66.79% A.
- Quant raw/final: 3.25 / B, 100% coverage.
- Current signals: Positive / Positive / Negative / Positive / Positive; overall POSITIVE; acceleration DECELERATING.
- Narrative axes derive CONFIRMED; no breaker.
- Market cap 11,235,672. Required future equity/EV 27,495,078. Required revenue CAGR: 40.14% / 29.22% / 22.00% at conservative/base/premium exits. Expectation Gap OVERLAP; confidence LOW.
- Investment Grade: initial B → confidence cap B → final B.

### Difference

PASS. Prior high-level B / POSITIVE / approximately B is reproduced.

## IONQ

### Source snapshot

- Annual: [2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1824920/000119312526071562/ionq-20251231.htm), filed 2026-02-25.
- Current: [2026 Q2 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1824920/000119312526341001/ionq-20260630.htm), filed 2026-08-10; prior-share comparison from the [2025 Q2 10-Q](https://www.sec.gov/Archives/edgar/data/1824920/000095017025104066/ionq-20250630.htm).
- Price: [historical price source](https://stockanalysis.com/stocks/ionq/history/), 2026-09-01 close $37.78.

### Normalized inputs

- Revenue 2023/2024/2025: 22,042 / 43,073 / 130,016; reconstructed comparable GP: 13,934 / 22,476 / 52,528.
- 2024/2025 FCF: -123,675 / -299,604. The PP&E investing cash line is used; internal-use software additions are not silently double-subtracted when no separate investing cash outflow is reported.
- Latest liquidity: 2,392,156; shares 221,919,191 / 362,592,722.
- H1 revenue 144,718 vs 28,260; GP 35,354 vs 15,618; FCF -273,364 vs -89,100.
- Current liquidity 2,118,969; June 30 shares 381,044,481 vs 269,600,132.
- Growth Scope is ACQUISITION_INFLUENCED.

### Engine output and independent reference

- Revenue CAGR 142.87% A; GP CAGR 94.16% A; burn +142.25% X; runway 95.81 months A; dilution 63.39% X; revenue/share +84.74% A.
- Raw score 2.80 / C; Cash Burn X + Dilution X cap produces final Quant D.
- Current: Positive / Positive / Negative / Negative / Positive → MIXED; Funding Stress and Commercial Inflection both true; acceleration ACCELERATING.
- Narrative Gate QUALIFIED.
- Market cap 14,395,860; required future equity/EV 46,632,667. Required revenue CAGR 126.63% / 104.62% / 91.30%. Expectation Gap NEGATIVE; confidence LOW.
- IG cap order: initial C → Narrative B → Quant C → Current B → Funding Stress C → confidence B → final C.

### Difference

Production and independent reference PASS. Quant, Current and Funding Stress match prior analysis. Prior “around D” IG differs from C: **MANUAL_CALC_ERROR**. Under frozen v1, a negative gap with LOW confidence starts at C, and the active caps have a maximum of C rather than D. No threshold was changed to force the prior result.

## ONDS

### Source snapshot

- Annual: [2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1646188/000121390026035981/ea0282911-10k_ondas.htm), available 2026-03-31.
- Current: [2026 Q2 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1646188/000119312526349288/onds-20260630.htm), filed 2026-08-13; prior shares cross-checked to the [official share roll-forward](https://www.sec.gov/Archives/edgar/data/1646188/000121390025074654/ea025264901ex99-2_ondas.htm).
- Price: [historical price source](https://stockscan.io/stocks/ONDS/price-history), 2026-09-01 close $7.04.

### Normalized inputs

- Revenue 2023/2024/2025: 15,691.430 / 7,193 / 50,731; GP: 6,381.174 / 345.183 / 20,156.
- 2024/2025 FCF: -35,166.623 / -40,818; latest liquidity 572,494.
- Shares: 93,173,191 / 380,763,481.
- H1 revenue 133,894 vs 10,522; GP 60,789 vs 4,821; FCF -146,472 vs -15,330.
- Current liquidity 1,384,493; shares 529,838,610 vs 206,732,666.
- Growth Scope is ACQUISITION_INFLUENCED; acquisition consideration and securities purchases are excluded from Growth CAPEX.

### Engine output and independent reference

- Revenue CAGR 79.81% A; GP CAGR 77.73% A; burn +16.07% D; runway 168.31 months A; dilution 308.66% X; revenue/share +72.58% A.
- Quant 2.95 / C.
- Current: Positive / Positive / Negative / Negative / Positive → MIXED; Funding Stress true; acceleration ACCELERATING.
- Narrative Gate DEVELOPING.
- Market cap 3,730,064; required future equity/EV 15,090,189. Required CAGR 150.76% / 126.41% / 111.67%. Expectation Gap NEGATIVE; confidence LOW.
- IG: initial C → Narrative C → Quant B → Current B → Funding Stress C → confidence B → final C.

### Difference

Production and independent reference PASS. Prior Quant/Current/Funding Stress match. Prior “around D” IG differs from C: **MANUAL_CALC_ERROR**, for the same frozen low-confidence initial-grade behavior described for IONQ.

## LPTH

### Source snapshot

- Annual: [fiscal 2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/889971/000165495425011130/lpth_10k.htm), available 2025-09-29.
- Current: [fiscal 2026 Q3 Form 10-Q](https://www.sec.gov/Archives/edgar/data/889971/000143774926015594/lpth20260331_10q.htm), filed 2026-05-07; prior shares from the [fiscal 2025 Q3 10-Q](https://www.sec.gov/Archives/edgar/data/889971/000165495425005945/lpth_10q.htm).
- Price: [historical regular-session data](https://www.investing.com/equities/lightpath-technologies-inc-historical-data), 2026-09-01 close $9.47.

### Normalized inputs

- Revenue FY2023/24/25: 32,933.949 / 31,726.192 / 37,202.630; GP 11,074.823 / 8,631.246 / 10,130.114.
- FY2024/25 FCF: -1,661.768 / -9,593.692; liquidity 4,877.036; shares 39,254,643 / 42,949,307.
- Nine-month revenue 50,559.747 vs 24,992.837; GP 17,459.185 vs 7,439.361; FCF -6,960.974 vs -6,262.173.
- Current cash 55,235.181; cover shares 62,789,407 vs 42,898,936.
- Annual is SAME_SCOPE; current is ACQUISITION_INFLUENCED because G5 and later acquisitions entered the comparison.

### Engine output and independent reference

- Revenue CAGR 6.28% D; GP CAGR -4.36% X; burn +477.32% X; runway 6.10 months D; dilution 9.41% C; revenue/share +7.17% D.
- Quant 0.85 / X.
- Current: Positive / Positive / Neutral / Negative / Positive → POSITIVE; Commercial Inflection true; acceleration ACCELERATING.
- Narrative Gate QUALIFIED.
- Market cap 594,616; required future equity/EV 1,757,294. Required CAGR 88.21% / 73.55% / 63.85%. Expectation Gap NEGATIVE; confidence LOW.
- IG: initial C → Narrative B → Quant C through Commercial Inflection exception → confidence B → final C.

### Difference

PASS. Prior X / POSITIVE / Commercial Inflection / approximately C is reproduced.

## EROC

### Source snapshot

- Annual/predecessor: [IPO S-1/A](https://www.sec.gov/Archives/edgar/data/2110029/000119312526258942/d12401ds1a.htm), filed 2026-06-05. It states ERock, Inc. was formed in January 2026 and supplies predecessor financials.
- Current: [2026 Q2 Form 10-Q](https://www.sec.gov/Archives/edgar/data/2110029/000119312526346922/eroc-20260630.htm), available 2026-08-12.
- Price: [NYSE at-close history](https://chartexchange.com/symbol/nyse-eroc/historical/), 2026-09-01 close $11.41.

### Normalized inputs

- No credible third comparable annual observation for the registrant: FY2023 mandatory fields remain null.
- Predecessor revenue 2024/2025: 128,490 / 183,145; GP 15,351 / 34,001; FCF -33,210 / +111,830.
- H1 revenue 71,614 vs 92,566; GP 12,624 vs 17,863; FCF +260,104 vs -1,975.
- Liquidity 660,861; June 30 Class A + B shares 219,400,080. Prior comparable registrant shares are unresolved due IPO/reorganization.
- Customer deposits materially drive CFO; the official number is retained and explicitly noted rather than adjusted ad hoc.

### Engine output and independent reference

- Revenue CAGR and GP CAGR unresolved; Cash Burn A; Runway A; shareholder metrics unresolved. Coverage 30%, mandatory coverage fails, so Quant is UNRESOLVED.
- Current: Negative / Negative / Positive / Unresolved / Neutral → NEUTRAL; acceleration unresolved; no stress/inflection/deterioration flag.
- Narrative Gate DEVELOPING.
- Market cap 2,503,355; required future equity/EV 8,109,145. Required CAGR 85.79% / 61.74% / 49.14%. Gap NEGATIVE, but credible exit evidence count is zero, so confidence is UNRESOLVED.
- IG: initial U → unresolved valuation-confidence gate U → final U.

### Difference

Production and independent reference PASS. Annual unresolved and final U match prior analysis. Prior Current MIXED differs from NEUTRAL: **MANUAL_CALC_ERROR**. The frozen aggregation has only one positive and two negative among four resolved signals; it therefore falls to NEUTRAL, not MIXED. The missing Funding signal is not filled with an IPO share estimate.

## Discrepancy register

| Company | Prior reference | Golden result | Classification | Resolution |
|---|---|---|---|---|
| IONQ | IG around D | IG C | MANUAL_CALC_ERROR | Preserve frozen low-confidence initial-grade and C caps. |
| ONDS | IG around D | IG C | MANUAL_CALC_ERROR | Preserve frozen low-confidence initial-grade and C caps. |
| EROC | Current MIXED | Current NEUTRAL | MANUAL_CALC_ERROR | Preserve resolved-count aggregation and unresolved share comparison. |

No DATA_NORMALIZATION, SOURCE_TIMING, ENGINE_BUG or SPEC_AMBIGUITY discrepancy was found in the production/reference comparison. The notable normalization risks—M&A scope, IONQ software capitalization presentation, LPTH fiscal-year timing, ONDS dilution, and EROC predecessor/share comparability—remain explicit in fixtures instead of becoming company exceptions.

## Reproduction

Run the full offline suite with `py -m pytest`. The five fixture files and `tests/test_case2_golden_validation.py` contain all test inputs; no website is contacted by pytest.
