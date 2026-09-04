# M12-B Case 1/2 Systematic Test — Data / Universe Research

Status: RESEARCH — AWAITING APPROVAL

Authoritative: NO

Implementation Allowed: NO unless separately approved; all eight decisions below require approval

Last Updated: 2026-09-04

## Purpose and boundary

M12-B will evaluate the frozen Case 1/2 framework on a pre-declared point-in-time
universe using the common [Generic Calibration Framework](../specs/calibration-framework-v1.md).
Unlike the curated Historical Stress Calibration, securities may not be selected because
their later outcomes are already known.

This document recommends a protocol; it does not approve it or authorize code. It does
not change any frozen threshold, weight, formula, Narrative rule, Valuation rule, or
Investment Grade rule. Optimization on the evaluation sample is prohibited.

## Executive recommendation

Use a US-only, earnings-driven, 2015–2025 research backtest. Select domestic operating
company common stocks at each historical decision date with point-in-time market cap of
at least USD 500 million and adequate liquidity. Use accession-scoped SEC filings as the
canonical fundamental source. Start with a free multi-source pilot for listing history,
prices, corporate actions, and delisted outcomes; evaluate a targeted paid source only
for blockers demonstrated by that pilot. Evaluate 1-year total return as the primary
outcome, with a fixed broad-market benchmark and sector benchmarks as supporting
diagnostics only.

Run the broad sample with Narrative unresolved unless contemporaneous, reproducible
evidence exists. A later, pre-declared stratified subset may test versioned Narrative
assessment. Do not describe Quant/Current/valuation-only output as a complete historical
Investment Grade.

## Eight approval gates

Each item remains **RECOMMENDED, NOT ACCEPTED**.

### Gate 1 — Universe v1

**Recommendation:** US-listed domestic operating-company common equities on NYSE,
Nasdaq, and NYSE American, determined point in time.

Include:

- active and subsequently delisted securities;
- bankruptcies, mergers, acquisitions, ticker changes, and exchange transfers;
- post-de-SPAC operating companies only after an eligible reporting history exists.

Exclude:

- ADRs and other foreign depositary receipts;
- ETFs, mutual funds, closed-end funds, preferred shares, warrants, rights, and units;
- blank-check/SPAC shells before an operating-company combination;
- securities whose identity or required point-in-time inputs remain unresolved.

Recommended eligibility floors, measured at the decision date:

- market capitalization at least USD 500 million; and
- trailing 60-trading-day median dollar volume at least USD 1 million.

The market-cap floor must use the last eligible price and actual contemporaneous shares
outstanding, never current market cap or diluted weighted-average shares. The liquidity
floor is an execution/data-quality screen, not a new investment metric.

Planning alternatives:

| Option | Point-in-time floors | Planning-size estimate | Bias / coverage | Data and delisting burden |
|---|---|---:|---|---|
| Lean | USD 1B cap / USD 2M median dollar volume | 1,500–2,500 | Favors established survivors and misses more early Case 2 outcomes | Lowest, but delisted names remain mandatory |
| Balanced — recommended | USD 500M / USD 1M | 2,500–4,000 | Retains material small/mid-cap growth without a microcap-dominated sample | Moderate; needs reliable corporate-action and terminal-payoff data |
| Broad | USD 300M / USD 1M | 3,500–5,000 | Best small-cap reach, but more listing-quality and liquidity selection effects | Highest; more bankruptcies, OTC transitions, sparse prices, and identifier breaks |

These counts are sizing estimates, not observed results. The selected provider pilot
must measure them before the protocol is frozen.

### Gate 2 — Geographic scope v1

**Recommendation:** US-only for v1; add Korea only in a separately approved v1.1 or v2.

The SEC offers filing timestamps and machine-readable filings under one disclosure
regime. Korea is feasible through OpenDART and KRX, but issuer identifiers, fiscal
taxonomy, historical shares, corporate actions, delisting proceeds, price adjustments,
and redistribution rights require a separate normalization and validation track.
Combining both markets now would make a failed test ambiguous between investment logic
and cross-market data engineering.

### Gate 3 — Snapshot cadence v1

**Recommendation:** earnings-driven snapshots after each eligible 10-Q or 10-K complete
information set becomes public.

- `period_end` is the reported fiscal period end.
- `available_at` is the filing/publication timestamp of the last required input.
- `as_of` is the decision timestamp and must be on or after every required
  `available_at`.
- The entry reference is the first executable market close after the complete
  information set became public. A release after the close moves execution to the next
  trading session.
- A new filing creates a new immutable fundamental analysis snapshot.
- Price-only refreshes may recalculate Valuation output against the same versioned
  assumptions, but are not independent fundamental observations and do not create a
  new Quant/Current signal.

A calendar-quarter cadence is easier but can reuse stale information unevenly and
create arbitrary timing. Earnings-driven cadence is closer to the engine's information
contract.

| Cadence | Point-in-time realism | Cost / correlation | Valuation use |
|---|---|---|---|
| Earnings-driven — recommended | Highest: event follows the actual information set | Moderate; overlapping observations must be clustered | One valuation at each new information state |
| Fixed calendar quarter | Uneven staleness across issuers | Moderate; easier scheduling but artificial dates | Comparable dates, less realistic decisions |
| Monthly | Fundamentals remain unchanged for many observations | Highest volume and strongest duplicate correlation | Useful only as explicitly linked price-only repricing |

### Gate 4 — Historical range v1

**Recommendation:** decision dates from 2015-01-01 through 2025-12-31, with earlier
lookback data loaded when a calculation requires it and outcome prices extending far
enough to resolve the final 1-year horizon.

This covers distinct rate, pandemic, speculative-growth, inflation, and tightening
regimes while staying within the comparatively mature XBRL era. A 2020–2025 sample is
too regime-concentrated; beginning much earlier materially increases taxonomy and
identifier reconstruction risk. Implementation should first prove a small 2018 pilot,
then run the pre-approved full range without changing rules.

| Range | Filing/XBRL and price burden | Regimes represented | Assessment |
|---|---|---|---|
| 2015–2025 — recommended | Highest of the three; still largely mature XBRL era | Growth bull, COVID shock, zero rates, inflation/tightening, 2022 bear | Best regime diversity |
| 2018–2025 | Moderate | Late-cycle, COVID, zero rates, tightening/bear | Good implementation pilot, weaker long-cycle evidence |
| 2020–2025 | Lowest | COVID and rate-cycle dominated | Too concentrated for the primary evaluation |

### Gate 5 — Point-in-time fundamentals source v1

**Recommendation:** accession-scoped SEC EDGAR filings and acceptance timestamps are
canonical. SEC submissions, XBRL Company Facts, and bulk files may discover candidates
and accelerate extraction, but the stored observation must retain accession, form,
filing/acceptance timestamp, taxonomy concept, reported period, unit, and retrieval
provenance.

Do not query today's Company Facts and assume every returned value was known historically;
amendments, restatements, concept changes, and multiple filing contexts must be resolved
against the filing available at `as_of`. Actual point-in-time shares outstanding should
come from the eligible filing/cover disclosure or another explicitly sourced historical
share observation.

Commercial normalized fundamentals may be used as a reproducibility/QA accelerator only
after license approval. They must not silently replace filing provenance.

| Candidate | PIT integrity / coverage | Shares and delistings | Rate / complexity | Cost and restrictions |
|---|---|---|---|---|
| SEC EDGAR + accession filing parse — recommended | Primary filing evidence and acceptance time; US domestic filings | Actual shares can be extracted; issuer history available, but no market delisting return | 10 requests/sec fair-access ceiling; highest parsing work | Free public filings; cache politely with provenance |
| Sharadar SF1/SFA | PIT dimensions, restated/as-reported views, active/delisted coverage from roughly 1997 | Delisted fundamentals strong; diluted-share fields are not consistently present | Batch/table API; plan limits and current platform path require confirmation | Premium, current public price not verifiable; license approval required |
| Intrinio US Fundamentals | Standardized and as-reported SEC-derived history, broadly from 2007 | Claims active/delisted coverage; actual-share and terminal-event completeness need pilot | Lower normalization effort; API/CSV/cloud delivery | Individual USD 150/month personal-only; commercial tiers higher |

### Gate 6 — Market, corporate-action, and delisting source v1

**Recommendation:** run a free-first, multi-source pilot. Use SEC and official exchange/
issuer evidence for identifiers and corporate actions where possible; compare multiple
free historical-price sources and explicitly reconstruct selected delisted outcomes.
Persist source/version metadata, extraction manifests, hashes, and permissible derived
results. Only measured gaps may trigger a targeted paid-provider decision. Norgate and
CRSP remain fallback/reference options, not prerequisites. Massive may support an API
pilot but is not a sole-source default because dividend-adjusted history is not currently
offered and terminal delisting-payoff completeness must be proved.

A source combination is acceptable only after a fixture pilot proves:

- historical point-in-time identifiers and listings;
- active and delisted securities without survivor filtering;
- split-safe and, for the primary outcome, total-return-safe prices;
- cash and stock distributions;
- mergers, ticker changes, reverse splits, bankruptcies, and delisting outcomes;
- historical shares or a reliable bridge to SEC shares;
- reproducible exports permitted by the license.

Free access is not assumed to mean complete, stable, or redistribution-safe. Norgate has
no general remote API and uses a local updater. CRSP access is commonly
through WRDS. Massive provides REST and flat files, with plan-specific request limits.
Exact throughput must be captured in the provider contract rather than assumed from a
marketing page.

### Gate 7 — Benchmark policy v1

**Recommendation:** one broad US-market benchmark is primary for every security; a
point-in-time assigned sector benchmark is supporting only.

Use a total-market series such as Russell 3000/CRSP US Total Market when licensed, or a
pre-declared investable proxy when not. The exact symbol/series and version must be
frozen before results. Benchmark assignment may not be selected after observing a
stock's performance.

Alpha is resolved only when stock and benchmark have the same return type and the same
effective start/end dates. Prefer total-return versus total-return. If only price return
is available, compare price return to price return and label it accordingly. A benchmark
failure never removes an otherwise valid stock return.

| Option | Interpretation and provider burden | Cherry-picking risk | Decision |
|---|---|---|---|
| A. One broad US benchmark | Clearest cross-company alpha; one licensed series | Lowest | Viable minimum |
| B. Broad benchmark by listing market | Exchange is not an economic exposure; extra series | Medium and hard to justify | Reject for v1 |
| C. Broad primary + sector supporting | Comparable primary alpha plus diagnostic industry context; needs PIT sector assignment | Controlled if both assignments are frozen before outcomes | Recommended |

### Gate 8 — Narrative mode v1

**Recommendation:** Mode B for the broad sample: Narrative remains `UNRESOLVED` unless a
reproducible point-in-time evidence package exists. Do not backfill today's knowledge or
invent a historical assessment to complete Investment Grade.

After the broad engine/data test, Mode C may be separately approved for a pre-declared,
stratified subset. It must freeze the evidence cutoff, sources, rubric version, KPI set,
review process, and any model/prompt version before outcomes are inspected.

| Mode | Treatment | Recommendation |
|---|---|---|
| A | Omit Narrative and report only eligible lower layers | Acceptable diagnostic, not full Investment Grade |
| B | First-class `UNRESOLVED` absent reproducible PIT evidence | Broad-sample default |
| C | Versioned human/LLM assessment on a pre-declared subset | Later validation stage only |

## Point-in-time valuation and Investment Grade feasibility

Full historical Investment Grade requires contemporaneous valuation evidence, not just
a historical price. Required-growth calculations also need the then-valid assumption
version and exit-multiple evidence. Current company/peer multiples, later consensus,
and hindsight terminal outcomes are prohibited.

Use three stages:

1. **Quant/Current data proof:** reproduce routing and frozen lower-layer calculations;
   store historical price and fixed required-return sensitivity. Any missing valuation
   evidence or Narrative stays unresolved. Do not claim a full grade.
2. **Valuation reconstruction:** add time-stamped company-history, comparable-company,
   and business/capital-model evidence; freeze conservative/base/premium ranges before
   reading subsequent returns.
3. **Narrative-enriched evaluation:** calculate complete Investment Grade only for
   observations where every required gate is valid under the approved Narrative mode.

Price-only updates may change valuation output while preserving the valuation assumption
version. They must remain clustered under the same fundamental information event.

## Delisting and corporate-action return policy

Every security receives a permanent internal `security_id`; ticker is a dated attribute.
Successor chains and corporate actions are explicit records, never inferred from today's
ticker alone.

- Cash acquisition: terminal value is the cash consideration on the effective date,
  including eligible distributions.
- Stock merger: convert holdings using the official exchange ratio and continue the
  successor series to the horizon.
- Mixed consideration: combine cash and converted successor shares.
- Bankruptcy/liquidation: use documented distributions or a provider's qualified
  delisting return. Use -100% only with evidence that common equity became worthless.
- Unresolved payoff or broken action chain: return remains `UNRESOLVED`; never assume
  zero return or drop the company.
- Reverse splits and ordinary splits must preserve economic value through an
  adjustment-safe series.

The denominator of every cohort must disclose resolved, partial, and unresolved outcome
counts so data failure cannot manufacture performance.

## Historical market-cap hierarchy

At each selection timestamp:

1. eligible prior-close market price;
2. actual shares outstanding on or nearest before that date, known at `as_of`;
3. if exact-date shares are absent, the latest explicitly disclosed period-end/cover
   shares known at `as_of`, with age and `PARTIAL` quality recorded;
4. corporate-action adjustments effective by that timestamp;
5. market cap = price × actual shares.

Provider-supplied historical market cap is acceptable only when methodology and
point-in-time status are documented. Current shares, later-restated values, diluted
weighted-average shares, and today's market cap are forbidden fallbacks. A missing
critical component makes market-cap eligibility unresolved.

## Data-quality contract

Each candidate/event records a generic coverage state:

- `COMPLETE`: all required point-in-time inputs and provenance pass;
- `PARTIAL`: some supporting inputs are absent, but the explicitly named calculation is
  still valid;
- `UNRESOLVED`: an eligibility or calculation-critical input is missing, mismatched, or
  post-dates `as_of`.

Required reason codes should include at least missing filing, taxonomy ambiguity,
stale/missing shares, identifier discontinuity, missing corporate action, unresolved
delisting payoff, unsafe price adjustment, benchmark mismatch, insufficient history,
and prohibited look-ahead. Unresolved never becomes zero, neutral, false, exclusion, or
a failed investment outcome.

## `BacktestRun` contract

Implementation should introduce one immutable run manifest containing at least:

- run ID, created timestamp, code commit, schema/spec versions, and configuration hash;
- approved universe, geography, exchanges, security types, size/liquidity filters;
- decision range, cadence, information cutoff, execution-price convention;
- Case/router version and every frozen engine version;
- fundamental, market, action, delisting, shares, and benchmark provider/version;
- return type, primary/secondary horizons, MDD coverage setting;
- benchmark assignment policy and exact benchmark IDs;
- Narrative mode, rubric/evidence version when applicable;
- source extract manifests/checksums and deterministic random seed if sampling occurs;
- resolved/partial/unresolved counts at every pipeline stage;
- parent run ID for a rerun and an explicit reason for any changed input.

The manifest is append-only. Rerunning with corrected data creates a new run and a
diff; it does not overwrite the earlier result.

## Overlapping observations and statistical unit

Quarterly/earnings-driven snapshots from the same company overlap at 1-year horizons
and are not independent bets. Report two views:

- **signal-event view:** every eligible snapshot, useful for engine diagnostics;
- **company-cluster view:** outcomes grouped by permanent company/security chain,
  primary for uncertainty and cross-sectional interpretation.

Price-only valuations within one filing event are one cluster and must not inflate the
sample. Initial v1 should report descriptive distributions and company-clustered counts,
not naive p-values. Any later bootstrap or inference method must be pre-declared before
results are examined.

## Outcomes and reporting

Primary horizon: **1-year total return and matched broad-market alpha**.

Secondary diagnostics:

- 1-month, 3-month, and 6-month matched returns;
- maximum drawdown when the frozen completeness contract passes;
- absolute return, benchmark return, alpha, and their effective dates;
- outcomes by Case, Quant Grade, Investment Grade where valid, Expectation Gap,
  Funding Stress, Commercial Inflection, and valuation confidence;
- coverage/failure rates and delisted contribution.

No portfolio turnover, transaction-cost, position-sizing, or deployable-strategy claim
belongs in v1. Avoid annualizing overlapping event observations.

## Feasibility mini-check

Existing repository fixtures establish three useful probes but not a systematic result:

- **ADBE FY2017:** an active issuer for SEC acceptance timing, adjusted prices, and a
  matched benchmark path.
- **SKLZ FY2021:** its June 2023 1-for-20 reverse split proves that raw ticker prices can
  be badly misleading without corporate-action handling.
- **VLDR FY2020:** Velodyne ceased trading in February 2023 and each share converted into
  0.8204 Ouster shares, proving that stock-merger successor chaining is required.

Before full implementation, run a read-only provider pilot for these three plus one cash
acquisition and one bankruptcy. Pass criteria are exact identity continuity, filing
cutoff, adjustment factors, terminal payoff/successor chain, matching benchmark dates,
and license-compliant reproducibility. A provider failure is recorded; the fixture is
not quietly replaced with a survivor.

## Provider and cost comparison

Prices are public list prices observed on 2026-09-04 and may change. Contract terms,
taxes, exchange fees, rate limits, permitted storage, and derived-output rights must be
confirmed before purchase.

| Provider | Fundamentals | Adjusted Price | Delisted | Corporate Actions | Point-in-Time | Approx Cost | Key Limitation |
|---|---|---|---|---|---|---:|---|
| SEC EDGAR | Canonical filings/XBRL | No | Filing history, not terminal return | Filing disclosures only | Acceptance timestamp/accession | Free; 10 requests/sec fair access | Parsing complexity; no market data |
| Sharadar SF1/SFA | Yes, standardized | Bundle-dependent | Active and delisted fundamentals | Actions table | PIT dimensions | Quote/login required | Premium license; share-field gaps; platform transition check |
| Intrinio | Yes, standardized/as-reported | Split-adjusted; dividend factors/data | Claims active/delisted coverage | Splits/dividends/reference | Filing-derived dates | USD 150/month individual; USD 333+/month startup | Personal plan bars redistribution/display; terminal payoff needs pilot |
| Norgate US Platinum | No | Daily adjusted history | Strong US delisted coverage | Included in adjusted/security history | Historical constituent/security data | USD 630/year | Personal/non-commercial; local updater; retention/export restrictions |
| CRSP via WRDS | No | Price and total-return research series | Strong, with delisting returns | Distributions/actions | Permanent IDs and historical observations | Institutional quote | Access and redistribution restrictions |
| Massive Advanced | No | Split-adjusted; not dividend-adjusted | Reference data includes inactive/delisted | Splits, dividends, ticker events | Dated reference endpoint | USD 199/month individual | Terminal payoff unproved; personal-use terms; no total-return series |
| Massive Business | No | Same underlying US market coverage | Reference data includes inactive/delisted | Splits/dividends/reference | Dated reference endpoint | USD 2,499/month | High cost; contract needed for derived/display use |
| OpenDART + KRX | Korean filings | KRX historical datasets | KRX listed/delisted datasets | Requires Korean normalization | Filing and dated market records | Public portals; licensing review pending | Separate Korea identity/action pipeline; not a single integrated source |

Official references:

- [SEC developer resources and fair-access policy](https://www.sec.gov/about/developer-resources)
- [SEC EDGAR API and bulk-data documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [Sharadar SF1 documentation](https://data.nasdaq.com/databases/SF1/documentation?anchor=exception-handling)
- [Sharadar/SFA bundle](https://data.nasdaq.com/databases/SFA)
- [Intrinio pricing](https://intrinio.com/pricing)
- [Intrinio US fundamentals](https://intrinio.com/products/us-fundamentals)
- [Norgate package pricing](https://norgatedata.com/stockmarketpackages.php)
- [Norgate data coverage](https://norgatedata.com/data-content-tables.php)
- [Norgate license](https://norgatedata.com/subscribe/eula.php)
- [CRSP research products](https://www.crsp.org/research/)
- [WRDS description of CRSP stock data](https://wrds-www.wharton.upenn.edu/pages/grid-items/crsp-stock-database-structure/)
- [Massive stock API documentation](https://massive.com/docs/rest/stocks)
- [Massive pricing](https://massive.com/stocks)
- [Massive market-data terms](https://massive.com/legal/market-data-terms-of-service)
- [OpenDART](https://opendart.fss.or.kr/intro/main.do)
- [KRX Data Marketplace](https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd?locale=en)
- [VLDR/Ouster merger filing](https://www.sec.gov/Archives/edgar/data/1816581/000119312523155611/d502854d424b3.htm)
- [SKLZ reverse-split disclosure](https://www.sec.gov/Archives/edgar/data/1801661/000180166123000030/sklz-20230630.htm)

## Staged implementation after approval

Approval would authorize the M12-B design freeze, not an immediate full run.

1. Freeze the eight M12-B decisions in an ADR and `CalibrationRun` configuration.
2. Build provider-neutral US identifiers, provenance, and coverage adapters outside the
   common kernel.
3. Complete the free-first five-security feasibility pilot and document exact blockers.
4. Evaluate a targeted paid source only where the free pilot cannot meet the contract.
5. Reproduce a small 2018 slice, including delisted securities and leakage tests.
6. Freeze the extraction manifest before observing investment outcomes.
7. Run 2015–2025 Case 1/2 Quant coverage through the common calibration kernel.
8. Add Current, Valuation, and Narrative incrementally under M12-C/D/E.

Stop if a provider cannot reproduce delistings, adjustment-safe returns, historical
shares, or the approved information timestamp. Do not compensate by changing frozen
investment logic.

## Decision Package

Implementation remains blocked until the owner explicitly accepts or replaces each
recommendation. Nothing below is `ACCEPTED`.

### 1. Universe v1

- **RECOMMENDED:** Balanced US operating-company common-stock universe; USD 500M cap
  and USD 1M trailing median dollar-volume floors, point in time.
- **ALTERNATIVES:** Lean USD 1B/USD 2M; Broad USD 300M/USD 1M.
- **WHY:** Preserves meaningful Case 2/small-growth coverage without making fragile
  microcap data the dominant engineering problem.
- **RISKS:** Market-cap/share staleness and liquidity screens can still create selection
  effects; all exclusions and unresolved candidates must be counted.
- **COST:** Estimated 2,500–4,000 securities per date before Case eligibility; provider
  pilot must replace this planning estimate.
- **BLOCKERS:** Survivorship-safe security master, historical actual shares, delisting
  outcomes, and corporate-action chain.

### 2. US-only vs US+KR

- **RECOMMENDED:** US-only v1.
- **ALTERNATIVES:** US+KR from launch; Korea-only parallel pilot.
- **WHY:** One filing and market identity regime makes data failures interpretable.
- **RISKS:** Initial conclusions may not generalize to Korea.
- **COST:** Avoids a second taxonomy, currency, calendar, identifier, and action pipeline.
- **BLOCKERS:** Korea expansion requires OpenDART/KRX licensing and end-to-end delisted
  security proof.

### 3. Snapshot Cadence v1

- **RECOMMENDED:** Earnings-driven after each complete 10-Q/10-K information set.
- **ALTERNATIVES:** Fixed calendar quarter; monthly price observations.
- **WHY:** Matches real fundamental information arrival and prevents arbitrary staleness.
- **RISKS:** Unequal event counts and overlapping 1-year outcomes.
- **COST:** Filing-event orchestration and company-cluster reporting.
- **BLOCKERS:** Reliable acceptance/release timestamps and exchange-session execution map.

### 4. Historical Date Range v1

- **RECOMMENDED:** 2015–2025, with required pre-2015 lookback and post-2025 outcome data.
- **ALTERNATIVES:** 2018–2025 implementation pilot; 2020–2025 low-cost sample.
- **WHY:** Best regime diversity among evaluated options without moving deeply into early
  XBRL normalization.
- **RISKS:** Earlier taxonomy and delisting data have more gaps.
- **COST:** Roughly eleven filing cohorts plus one-year forward prices.
- **BLOCKERS:** Licensed history and measured completeness across early years.

### 5. Fundamental Data Source v1

- **RECOMMENDED:** Accession-scoped SEC filings as canonical; Company Facts/bulk data for
  discovery; optional commercial source only for QA/normalization.
- **ALTERNATIVES:** Sharadar primary; Intrinio primary.
- **WHY:** Best auditability of exactly what was public at `as_of` and no source fee.
- **RISKS:** Taxonomy/context ambiguity and substantial parsing work.
- **COST:** SEC free at 10 requests/sec fair-access; Sharadar quote required; Intrinio
  USD 150/month individual or USD 333+/month startup.
- **BLOCKERS:** Filing-context resolver, actual-share extraction, issuer/security mapping,
  cache/provenance policy.

### 6. Market Data Source v1

- **RECOMMENDED:** Free-first multi-source pilot; buy only the smallest targeted source
  needed to close a demonstrated blocker.
- **ALTERNATIVES:** Norgate personal-research fallback; CRSP/WRDS research-grade fallback;
  Massive API pilot; contracted commercial feed.
- **WHY:** Tests feasibility before making one paid vendor an architectural dependency
  and keeps the common kernel provider-neutral.
- **RISKS:** Free sources may fail survivorship-safe universe, dividend adjustment, or
  terminal delisting payoff requirements; unresolved coverage must remain visible.
- **COST:** Initial data cost USD 0 plus engineering time. Fallback reference prices:
  Norgate USD 630/year; Massive Advanced USD 199/month; Massive Business USD 2,499/month;
  CRSP quote/access required.
- **BLOCKERS:** Free five-security pilot, redistribution/storage review, and explicit gap
  report before any paid-provider selection.

### 7. Benchmark Policy v1

- **RECOMMENDED:** Fixed broad US total-market primary plus preassigned PIT sector
  benchmark supporting.
- **ALTERNATIVES:** Broad-only; benchmark by listing market.
- **WHY:** Retains one comparable primary alpha while exposing sector context without
  changing the yardstick after results.
- **RISKS:** PIT sector classification and total-return benchmark licensing.
- **COST:** One primary series plus sector series/assignment history.
- **BLOCKERS:** Freeze exact benchmark IDs, return basis, provider, and assignment version.

### 8. Narrative Backtest Mode v1

- **RECOMMENDED:** Mode B: `UNRESOLVED` absent reproducible PIT evidence; later Mode C on
  a pre-declared stratified subset.
- **ALTERNATIVES:** Mode A lower-layer-only broad test; Mode C for the whole universe.
- **WHY:** Preserves frozen Narrative gates without manufacturing hindsight evidence.
- **RISKS:** Broad-sample Investment Grade coverage will be incomplete; later human/LLM
  work remains model/version dependent.
- **COST:** Low for Mode B; high research/reviewer/model cost for Mode C.
- **BLOCKERS:** Versioned evidence corpus, rubric, KPI set, reviewer process, and model/
  prompt version before any Narrative-enriched run.

See [M12 in the roadmap](../roadmap.md) and the [market-data plan](market-data-plan.md).
