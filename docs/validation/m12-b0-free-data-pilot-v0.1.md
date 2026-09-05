# M12-B0 Free-First Data Pilot v0.1

Status: VALIDATION — COMPLETE WITH FAIL VERDICT

Authoritative for Results: YES

Authoritative for Investment Rules: NO

Last Updated: 2026-09-04

M12-A checkpoint: `d8a73373efddc8737615a864be193f7c96436de8`

## 1. Pilot scope

This validation measures whether free data can create an unbiased point-in-time Case 1/2
Quant → future outcome dataset at 2018, 2021, and 2022 anchors. It does not perform the
2015–2025 run, Current Trend, Valuation, Narrative, Investment Grade, full Router,
threshold optimization, or paid-provider integration.

Frozen Case 1/2 policy and the Generic Calibration Kernel were not changed. B0 code adds
only provider-neutral research contracts, deterministic sampling, manifest validation,
and documentation.

## 2. Data sources

The detailed matrix and executed access observations are in the
[Free-First Data Pilot research note](../research/free-data-pilot-v1.md). Official SEC
filings remain canonical financial evidence. SEC EFTS/full indexes were evaluated for
discovery; Nasdaq Trader for current listing discovery; Yahoo, Alpha Vantage, and Stooq
for prices; OpenDART/KRX for the KR portability spike.

## 3. US historical universe approach

The attempted method was SEC annual-filing discovery followed by a historical
security-level exchange-membership crosswalk. SEC returned filing records, but no tested
free source established permanent security identity, historical listing intervals, and
inactive/delisted continuity. Today's Nasdaq symbol directory was rejected because it is
not point-in-time.

The result is `UNRESOLVED`, not an empty universe. No surviving-ticker list was used.

## 4. Sample selection method

- seed: `youngrich-m12-b0-free-first`
- version: `sha256-permanent-security-id-v1`
- cap: 200 per anchor
- unit: permanent security identity after point-in-time membership validation

The implementation is deterministic, provider-order independent, duplicate-safe, and
does not replace difficult selections. Because membership never resolved, it was not run
against fabricated candidates.

## 5–8. Eligibility, metric, and performance coverage

| Anchor | Filing discovery records returned | Validated securities | Sampled | Case 1 eligible / resolved | Case 2 eligible / resolved | Price performance resolved |
|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 100 | 0 | 0 | 0 / 0 | 0 / 0 | 0 |
| 2021 | 100 | 0 | 0 | 0 / 0 | 0 / 0 | 0 |
| 2022 | 100 | 0 | 0 | 0 / 0 | 0 / 0 | 0 |
| **Total** | **300** | **0** | **0** | **0 / 0** | **0 / 0** | **0** |

The EFTS “total 10,000” value is a capped search value, not an exact universe size. The
100 returned records per query are attempted discovery N only. Promoting them to
security candidates would misstate identity and membership quality.

Metric coverage is therefore N=0 for every Case 1 and Case 2 Core metric. Raw-value
research fields are supported by `MetricResearchObservation`, but no real systematic
raw-metric/grade/outcome row was produced. Six-month return, one-year return, MDD, and
Alpha coverage are all N=0. No empty calibration table is interpreted as evidence.

## 9. Corporate-action and delisted stress set

The stress set is outcome-aware and excluded from calibration statistics.

| Sample | Purpose | Historical Quant | Performance | Result |
|---|---|---|---|---|
| FSLY FY2021 | Resolved-failure control | UNRESOLVED: full input set absent | RESOLVED in M11 | Useful performance plumbing control only. |
| SKLZ FY2021 | Reverse split / failure | UNRESOLVED | UNRESOLVED | Free configured price source lacked an adjustment-safe series. |
| VLDR FY2020 | Merger / delisting | UNRESOLVED | UNRESOLVED | Price continuity, merger consideration, and delisted payoff unresolved. |

No replacement company was inserted after these failures.

## 10. Quant calibration pilot tables

No metric-grade or Quant-grade outcome table is emitted because systematic N=0. Existing
M11 cohort numbers are not copied: those samples are curated, outcome-aware, and lack
reproducible historical Quant inputs. This separation prevents accidental strategy claims.

## 11. Data-quality breakdown

Systematic anchor pipeline:

| Reason | Occurrences | Effect |
|---|---:|---|
| `universe_membership_unavailable` | 3 anchors | Candidate, sample, Case, and outcome stages remain unresolved. |

Separate stress evidence:

| Reason | Samples |
|---|---|
| historical analysis input absent (`other`) | FSLY, SKLZ, VLDR |
| `price_unavailable` | SKLZ, VLDR |
| `corporate_action_unsafe` | SKLZ, VLDR |
| `delisted_payoff_unresolved` | VLDR |

Source-access failures are recorded in research notes but are not confused with missing
source coverage. For example, the official SEC archive exists even though direct
`master.idx` access from this environment was blocked.

## 12. Free-data feasibility verdict

**FAIL for M12-B1 entry.**

Free official filings can support ordinary-company financial reconstruction, and the
existing frozen adapters/kernel are reusable. However, B0 did not produce a validated
historical security universe or any systematic Quant/outcome record. Proceeding with a
current surviving-symbol list would create material survivorship bias, while silently
dropping SKLZ/VLDR-like observations would make failure coverage non-random.

This verdict is about the tested data stack, not the M12-A architecture and not the
investment rules. M12-B remains active at the data-pilot gate; M12-B1 must not start.

## 13. Paid-data blocker

One concrete blocker triggers evaluation: a historical US security master with permanent
identity, exchange-membership intervals, corporate actions, delisted securities, and
delisting outcomes. Free/official archived alternatives should be investigated first.
Norgate Current & Past or CRSP security/name/delisting files are narrow fallback
candidates; neither is purchased or integrated.

## 14. KR feasibility

The [KR feasibility spike](../research/kr-backtest-data-feasibility-v0.1.md) finds the
architecture portable and official-source coverage promising, but historical identity,
adjusted-price, corporate-action, automated-access, and license questions remain. KR
systematic N=0; verdict is architectural `PASS_WITH_GAPS`, not execution approval.

## 15. What cannot yet be concluded

- Whether any Case 1 or Case 2 metric grade is monotonic with future return.
- Whether Quant A/B/C/D/X separates return, Alpha, or MDD.
- Whether Case 2 dilution coverage is adequate.
- Whether free-price gaps are tolerable without survivor bias.
- Whether any frozen threshold, weight, eligibility rule, or guardrail should change.

## Architecture acceptance review

| Criterion | Result |
|---|---|
| Free PIT normalized inputs for ordinary US equities | PARTIAL: official filings are usable, but no unbiased selected historical security completed the chain. |
| Case 1 adapter needs no backtest formula | PASS by frozen adapter regression; not exercised on a B0 cohort row. |
| Case 2 adapter needs no backtest formula | PASS by frozen adapter/golden regression; not exercised on a B0 cohort row. |
| Same Generic Calibration Kernel consumes both | PASS by M12-A regression. |
| Raw metric + grade + future outcome dataset produced | FAIL: systematic N=0. |
| Unresolved remains visible | PASS. |
| Corporate-action/delisted failures explicit | PASS. |
| No Case-specific kernel logic | PASS. |
| KR targets the same contract | PASS at architecture level. |
| No paid provider used for convenience | PASS. |

## Research findings

- `HISTORICAL_US_SECURITY_MEMBERSHIP_FREE_SOURCE_GAP` — REQUIRES_VALIDATION.
- `DELISTED_PRICE_FREE_SOURCE_GAP` — OBSERVED.
- `SYSTEMATIC_QUANT_OUTCOME_DATASET_NOT_PRODUCED` — OBSERVED.

None is a `CHANGE_CANDIDATE`. No policy change is authorized.

## Follow-up: M12-B0.1 Tiingo Free Price Pilot

The [Tiingo research follow-up](../research/tiingo-data-pilot-v0.1.md) adds a provider
adapter, cache/rate-limit handling, full EOD field preservation, and guarded price-basis
normalization. Its 2026-09-05 live run resolved 10 of 12 bounded price series and passed
the selected split/dividend semantics checks. VLDR/BBBY, terminal payoff, and historical
identity remained unresolved. M12-B0.1 is `LIVE PRICE PILOT PASS WITH GAPS`.

This follow-up does not replace or soften the M12-B0 **FAIL for M12-B1 entry**. Historical
security membership, delisted continuity, and terminal outcomes remain unresolved, and
M12-B1 is not authorized.
