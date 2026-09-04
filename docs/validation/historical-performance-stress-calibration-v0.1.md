# Historical Performance Stress Calibration v0.1

> Historical Stress Calibration v0.1 is intentionally curated and outcome-aware. It validates analysis/performance plumbing and diagnostic behavior. It is not an unbiased strategy backtest and must not be used to claim proven alpha or statistically reliable expected returns.

Status: VALIDATION — COMPLETE

Authoritative for Results: YES

Authoritative for Investment Rules: NO

Outcome-aware: YES

Unbiased Backtest: NO

Performance checkpoint: `74a05649965b5d05b1f45a851e6fb283650821c5`

Research snapshot: 2026-09-04

## Scope and integrity

This basket intentionally contains known winners and failures. It tests point-in-time
anchors, immutable downstream performance, adjustment-safe horizons, benchmark
comparability, cohort plumbing, and honest unresolved states. **Historical Stress
Calibration v0.1 is NOT an unbiased strategy backtest.** It does not demonstrate
strategy alpha, statistical superiority of any grade, or optimal thresholds.

The SEC filing acceptance timestamp is `information_available_at` and `analysis_as_of`.
The reference price is the first provider EOD close strictly after that timestamp. This
is a deterministic daily-data execution convention: after-close filings move to the
next session; pre-close filings use that session close. Future prices enter only the
downstream `PerformanceSnapshot`.

All 13 detailed historical Quant/Narrative/Valuation input sets are unavailable in the
repository and are explicitly `ANALYSIS_INPUT_INCOMPLETE`. Canonical Investment Grades
are retained only where the project instruction preserved an exact grade. Missing
Current Trend, Funding Stress, Commercial Inflection, Thesis Status, and most
Expectation Gap states remain unresolved rather than false or zero. ADBE FY2021's
explicit “excessive market expectation / valuation” description is retained as a thin
research label (`NEGATIVE`), not reconstructed as a fabricated `ValuationSnapshot`.

## Data contract

- Filing anchor: SEC EDGAR submission and primary filing, including acceptance time.
- Stock and benchmark prices: Yahoo Finance Chart API daily OHLC close observations,
  frozen into offline JSON on 2026-09-04.
- Price basis: provider series treated as `SPLIT_ADJUSTED`; return type is
  `PRICE_RETURN`. It is not treated as total return.
- Adjustment version: `yahoo_chart_v8_split_adjusted_2026-09-04`.
- Benchmark: explicit SPY assignment v1 for this US-listed stress exercise.
- MDD: standard v1 completeness contract, `mdd_max_gap_days=7`. Every resolved series
  has 252–255 observations and a maximum calendar gap of four days.
- Tests perform no network access. The research curator is separate from runtime/test
  code and is not imported by pytest.

## Top-level result

| Company / Snapshot | Case | IG | Expectation Gap | Funding Stress | 1M | 3M | 6M | 1Y | 1Y MDD | 1Y Alpha |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| Adobe FY2017 | Case 1 | B | UNRESOLVED | UNRESOLVED | +4.82% | +12.60% | +29.68% | +22.51% | -25.53% | +29.53% |
| Adobe FY2021 | Case 1 | D | NEGATIVE* | UNRESOLVED | -10.75% | -20.34% | -24.57% | -30.47% | -48.65% | -21.46% |
| PayPal FY2021 | Case 1 | C | UNRESOLVED | UNRESOLVED | -20.76% | -26.46% | -23.08% | -34.70% | -46.42% | -26.04% |
| NVIDIA FY2018 — Supporting / Boundary | Supporting / Boundary | B* | UNRESOLVED | UNRESOLVED | -4.81% | +10.94% | +22.17% | -32.63% | -56.08% | -37.38% |
| Palantir FY2021 | Case 2 | B | UNRESOLVED | UNRESOLVED | +13.19% | -36.18% | -31.53% | -31.61% | -58.99% | -24.16% |
| CrowdStrike FY2020 | Case 2 | B | UNRESOLVED | UNRESOLVED | +25.59% | +80.88% | +133.56% | +216.76% | -25.85% | +157.39% |
| Cloudflare FY2020 | Case 2 | C | UNRESOLVED | UNRESOLVED | -8.65% | +7.99% | +63.44% | +57.39% | -63.14% | +42.59% |
| Shopify FY2015 | Case 2 | B | UNRESOLVED | UNRESOLVED | +21.37% | +19.80% | +73.18% | +175.01% | -18.97% | +153.13% |
| Tesla FY2014 | Case 2 | C | UNRESOLVED | UNRESOLVED | -9.02% | +21.68% | +19.50% | -5.61% | -49.10% | +2.51% |
| MongoDB FY2020 | Case 2 | B | UNRESOLVED | UNRESOLVED | +18.84% | +65.90% | +69.69% | +90.35% | -38.87% | +39.48% |
| Fastly FY2021 | Case 2 | D | UNRESOLVED | UNRESOLVED | +7.74% | -27.56% | -52.84% | -24.67% | -62.21% | -15.51% |
| Skillz FY2021 | Case 2 | D | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |
| Velodyne FY2020 | Case 2 | D/X range | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |

`NEGATIVE*` is research metadata supported by the preserved historical interpretation;
the full versioned valuation assumptions are unavailable, so the AnalysisSnapshot
valuation component remains unresolved.

## Cohort analytics — 1Y

These are actual `performance_analytics.py` outputs. Unresolved values are excluded only
from their metric denominator.

### Investment Grade

| IG | N total | 1Y resolved | Mean | Median | Min | Max | Positive rate | Median MDD | Mean Alpha | Median Alpha |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B | 6 | 6 | +73.40% | +56.43% | -32.63% | +216.76% | 66.67% | -32.36% | +53.00% | +34.51% |
| C | 3 | 3 | +5.69% | -5.61% | -34.70% | +57.39% | 33.33% | -49.10% | +6.35% | +2.51% |
| D | 3 | 2 | -27.57% | -27.57% | -30.47% | -24.67% | 0.00% | -55.43% | -18.49% | -18.49% |
| UNRESOLVED | 1 | 0 | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED | UNRESOLVED |

There is no A sample; none was manufactured. The B row includes NVIDIA's explicitly
marked boundary observation.

### Case / boundary role

| Group | N total | 1Y resolved | Mean | Median | Positive rate | Median MDD | Mean Alpha |
|---|---:|---:|---:|---:|---:|---:|---:|
| Case 1 calibration | 3 | 3 | -14.22% | -30.47% | 33.33% | -46.42% | -5.99% |
| Case 2 calibration | 9 | 7 | +68.23% | +57.39% | 57.14% | -49.10% | +50.78% |
| Supporting / Boundary | 1 | 1 | -32.63% | -32.63% | 0.00% | -56.08% | -37.38% |

### Expectation Gap

| Gap | N total | 1Y resolved | Mean / Median 1Y | Median MDD | Mean / Median Alpha |
|---|---:|---:|---:|---:|---:|
| NEGATIVE | 1 | 1 | -30.47% / -30.47% | -48.65% | -21.46% / -21.46% |
| UNRESOLVED | 12 | 10 | +43.28% / +8.45% | -47.76% | +32.16% / +5.99% |

N=1 is diagnostic only. It cannot establish valuation usefulness statistically.

### Funding Stress and Commercial Inflection

All 13 states are unresolved because no point-in-time Current Trend snapshots were
preserved. `UNKNOWN` is not converted to `NO`; therefore no YES/NO comparison is valid.

## Company diagnostics

Each anchor below links to the official filing. Price observations and full provider
URLs are stored beside the sample in `tests/fixtures/performance_historical/`.

### Adobe FY2017

- Historical anchor: [FY2017 10-K](https://www.sec.gov/Archives/edgar/data/796343/000079634318000015/adbe10kfy17.htm), accepted 2018-01-22 21:07:26Z; reference 2018-01-23 close, $200.09; canonical IG B.
- Performance inputs: split-adjusted price return, Yahoo Finance offline daily series,
  explicit SPY v1; 252 observations, max gap four days.
- Forward performance: +4.82% / +12.60% / +29.68% / +22.51%; MDD -25.53%; alpha +29.53%.
- Diagnostic: the B bucket retained a profitable-growth winner without requiring a
  cheap-valuation label.

### Adobe FY2021

- Historical anchor: [FY2021 10-K](https://www.sec.gov/Archives/edgar/data/796343/000079634322000032/adbe-20211203.htm), accepted 2022-01-21 21:03:34Z; reference 2022-01-24 close, $519.66; canonical IG D.
- Performance inputs: same standardized basis and SPY assignment; 252 observations.
- Forward performance: -10.75% / -20.34% / -24.57% / -30.47%; MDD -48.65%; alpha -21.46%.
- Diagnostic: the preserved excessive-expectation case had weak one-year payoff, but it
  is only one outcome-aware observation.

### PayPal FY2021

- Historical anchor: [FY2021 10-K](https://www.sec.gov/Archives/edgar/data/1633917/000163391722000027/pypl-20211231.htm), accepted 2022-02-03 21:55:53Z; reference 2022-02-04 close, $126.08; canonical IG C.
- Forward performance: -20.76% / -26.46% / -23.08% / -34.70%; MDD -46.42%; alpha -26.04%.
- Diagnostic: this C watch case deteriorated; missing historical valuation detail was not
  reconstructed after seeing the loss.

### NVIDIA FY2018 — Supporting / Boundary

- Historical anchor: [FY2018 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581018000010/nvda-2018x10k.htm), accepted 2018-02-28 21:31:19Z; reference 2018-03-01 split-adjusted close, $5.8053; canonical B*.
- Forward performance: -4.81% / +10.94% / +22.17% / -32.63%; MDD -56.08%; alpha -37.38%.
- Diagnostic: the semiconductor cycle makes this a boundary observation, not pure Case
  1 calibration. Its one-year drawdown illustrates why later fame cannot rewrite the
  chosen horizon.

### Palantir FY2021

- Historical anchor: [FY2021 10-K](https://www.sec.gov/Archives/edgar/data/1321655/000119312522050913/d273589d10k.htm), accepted 2022-02-24 11:20:34Z; same-day close $11.83; canonical IG B.
- Forward performance: +13.19% / -36.18% / -31.53% / -31.61%; MDD -58.99%; alpha -24.16%.
- Diagnostic: B did not prevent a poor one-year outcome. This is a false-positive review
  candidate, not permission to optimize a threshold.

### CrowdStrike FY2020

- Historical anchor: [FY2020 10-K](https://www.sec.gov/Archives/edgar/data/1535527/000153552720000006/crwd-20200131.htm), accepted 2020-03-23 20:06:34Z; reference 2020-03-24 close, $14.3325; canonical IG B.
- Forward performance: +25.59% / +80.88% / +133.56% / +216.76%; MDD -25.85%; alpha +157.39%.
- Diagnostic: the B bucket retained a major Case 2 winner.

### Cloudflare FY2020

- Historical anchor: [FY2020 10-K](https://www.sec.gov/Archives/edgar/data/1477333/000147733321000009/cloud-20201231.htm), accepted 2021-02-25 21:26:35Z; reference 2021-02-26 close, $73.97; canonical IG C.
- Forward performance: -8.65% / +7.99% / +63.44% / +57.39%; MDD -63.14%; alpha +42.59%.
- Diagnostic: C retained substantial upside but also extreme path risk, consistent with
  an active-watch/optionality bucket rather than a low-risk recommendation.

### Shopify FY2015

- Historical anchor: [FY2015 20-F](https://www.sec.gov/Archives/edgar/data/1594805/000159480516000019/shopify20fbody.htm), accepted 2016-02-17 12:41:49Z; same-day split-adjusted close $2.2370; canonical IG B.
- Forward performance: +21.37% / +19.80% / +73.18% / +175.01%; MDD -18.97%; alpha +153.13%.
- Diagnostic: B retained the early winner. Provider back-adjustment is versioned; no
  raw pre-split price is substituted.

### Tesla FY2014

- Historical anchor: [FY2014 10-K](https://www.sec.gov/Archives/edgar/data/1318605/000156459015001031/tsla-10k_20141231.htm), accepted 2015-02-26 22:13:26Z; reference 2015-02-27 split-adjusted close $13.5560; canonical IG C.
- Forward performance: -9.02% / +21.68% / +19.50% / -5.61%; MDD -49.10%; alpha +2.51%.
- Diagnostic: one-year payoff was near flat with severe drawdown. A company becoming a
  later winner does not turn this selected one-year result positive.

### MongoDB FY2020

- Historical anchor: [FY2020 10-K](https://www.sec.gov/Archives/edgar/data/1441816/000144181620000067/mdb-013120x10k.htm), accepted 2020-03-27 21:04:53Z; reference 2020-03-30 close, $136.43; canonical IG B.
- Forward performance: +18.84% / +65.90% / +69.69% / +90.35%; MDD -38.87%; alpha +39.48%.
- Diagnostic: B retained another high-upside Case 2 company despite meaningful path risk.

### Fastly FY2021

- Historical anchor: [FY2021 10-K](https://www.sec.gov/Archives/edgar/data/1517413/000151741322000038/fsly-20211231.htm), accepted 2022-03-01 22:24:47Z; reference 2022-03-02 close, $17.96; canonical IG D.
- Forward performance: +7.74% / -27.56% / -52.84% / -24.67%; MDD -62.21%; alpha -15.51%.
- Diagnostic: the resolved failure sample remained in D and subsequently showed both
  weak return and severe drawdown.

### Skillz FY2021

- Historical anchor: [FY2021 10-K](https://www.sec.gov/Archives/edgar/data/1801661/000162828022004552/sklz-20211231.htm), accepted 2022-03-01 21:48:43Z; canonical IG D.
- Performance: UNRESOLVED. The configured Yahoo endpoint no longer returned a usable
  historical series at curation time; no RAW or guessed substitute was used.
- Diagnostic: failure classification is retained, but subsequent performance cannot be
  claimed from this fixture. Classification: `PRICE_SOURCE`, `HISTORICAL_INPUT_GAP`.

### Velodyne FY2020

- Historical anchor: [FY2020 10-K](https://www.sec.gov/Archives/edgar/data/1745317/000162828021004964/vldr-20201231.htm), accepted 2021-03-17 10:39:35Z; preserved canonical range D/X, exact grade unresolved.
- Performance: UNRESOLVED. The delisted symbol's configured provider endpoint did not
  provide the required adjustment-safe history; no survivor-only replacement or raw
  series was introduced.
- Diagnostic: the intended failure bucket is preserved but neither exact grade nor
  performance is used in numerical cohorts. Classification: `PRICE_SOURCE`,
  `HISTORICAL_INPUT_GAP`.

## Diagnostic answers

### Winner retention

ADBE FY2017, CRWD, SHOP, and MDB were retained in B and delivered positive one-year
returns. NET remained in C and delivered +57.39%. TSLA remained in C but its selected
one-year return was -5.61%; later success is outside this horizon. Thus the basket shows
that B/C can retain optionality, while PLTR and the NVIDIA boundary sample demonstrate
that these buckets are not guarantees.

### Failure rejection

FSLY remained D and produced -24.67% with -62.21% MDD. SKLZ remained D and VLDR retained
its D/X failure range, but their price outcomes are unresolved. Rejection classification
is preserved for all three; forward-return evidence is complete for only one.

### Valuation usefulness

The only sufficiently explicit NEGATIVE Expectation Gap sample is ADBE FY2021, with
-30.47% return and -48.65% MDD. This is directionally consistent with valuation being
useful, but N=1 cannot support a general claim.

### Funding Stress usefulness

Cannot be evaluated. No historical Funding Stress state was recoverable, and unknown was
not reclassified as NO.

### C-grade behavior

NET (+57.39%), TSLA (-5.61%), and PYPL (-34.70%) span strong optionality, near-flat
performance, and deterioration. In this curated basket C behaves more like an active
watch/optionality bucket than a homogeneous junk bucket, but its path risk is high.

## Discrepancy register

| Sample | Classification | Finding |
|---|---|---|
| All 13 | HISTORICAL_INPUT_GAP | Detailed original Quant/Narrative/Valuation inputs are not present; only explicitly preserved canonical states are used. |
| SKLZ FY2021 | PRICE_SOURCE, HISTORICAL_INPUT_GAP | Adjustment-safe history unavailable from configured provider; all performance unresolved. |
| VLDR FY2020 | PRICE_SOURCE, HISTORICAL_INPUT_GAP | Delisted-symbol history unavailable and exact D/X grade not preserved; performance and exact IG unresolved. |

No `ENGINE_BUG`, `HORIZON_ALIGNMENT`, or `BENCHMARK_ALIGNMENT` discrepancy appeared in
the 11 resolved samples. All resolved alpha pairs have matching return type and effective
start/end dates. The standardized daily-close entry convention is explicit; no
company-specific horizon was introduced.

## What appears promising

- The immutable pipeline reproduces 1M/3M/6M/1Y return, one-year MDD, and comparable
  SPY alpha for 11 different historical anchors without changing analysis snapshots.
- B/C retained several large winners, while the resolved D failure showed poor payoff.
- Unresolved values remain visible in denominators and do not silently become zero/NO.

## What appears weak

- Detailed historical analysis inputs are missing, so false-positive/false-negative
  diagnosis cannot yet be traced to individual Quant, Narrative, or Valuation gates.
- The basket is outcome-selected and tiny. Results are dominated by a few large winners.
- Daily EOD reference prices cannot represent intraday execution and Yahoo is a
  third-party provider rather than an exchange-grade corporate-action master.
- Funding Stress and Commercial Inflection diagnostics have no preserved labels.

## What cannot yet be concluded

This work cannot establish unbiased expected return, strategy alpha, statistical
significance, optimal grade thresholds, optimal Quant weights, or an optimal required
return. It does not justify changing any frozen investment logic.

## Appendix: Future Systematic Historical Backtest

This is a distinct, unimplemented project. It requires a pre-defined point-in-time
universe and deterministic eligibility/entry schedule; inclusion of delisted securities;
survivorship-bias controls; unrevised point-in-time fundamentals, market cap, share count,
and filing `available_at`; historical routing using only then-available evidence;
corporate-action-safe prices; and explicit versioned benchmarks. The universe and entry
schedule are intentionally not frozen here. Companies must never be selected because we
already know that they later won or failed.

No systematic universe backtest, provider client, SEC batch ingestion, threshold
optimization, ML, sizing, costs, taxes, execution, dashboard, alerting, or Case 3+ logic
is implemented by this calibration.
