# Free-First Data Pilot v1

Status: RESEARCH

Authoritative: NO

Implementation Allowed: NO unless separately approved

Last Updated: 2026-09-04

## Question and boundary

M12-B0 asks whether free sources can produce a point-in-time security universe, frozen
Case 1/2 Quant inputs, and adjustment-safe forward outcomes without silently introducing
survivorship bias. It does not select a production provider, change investment logic, or
authorize M12-B1.

The provider boundary is implemented in `engine/research_data/`. A universe source must
first emit permanent security identities valid at the anchor date. Filing sources then
emit normalized point-in-time Case inputs, and price sources emit adjustment-safe series.
SEC, DART, exchange, and vendor behavior does not enter the Generic Calibration Kernel.

## Sources evaluated

| Source | Role | Free? | PIT Universe | Filings | Shares | Adjusted Price | Delisted | Corporate Actions | Limitations |
|---|---|---:|---|---|---|---|---|---|---|
| [SEC EDGAR indexes and filings](https://www.sec.gov/about/developer-resources) | US filing discovery and canonical evidence | Yes | Filing universe only; not security membership | Yes | XBRL/filing dependent | No | Filings retained | Filing disclosures only | CIK is an issuer identifier, not a permanent listed-security identifier; exchange membership and security continuity need another source. Fair-access limit is 10 requests/second. |
| [SEC submissions / Companyfacts](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Filing metadata and XBRL extraction support | Yes | No | Supporting, not a replacement for accession filing | Often, taxonomy dependent | No | Issuers may remain discoverable | No complete action-adjusted series | No API key; normalized concepts, duration selection, amendments, and actual-share scope still require deterministic rules. |
| [Nasdaq Trader Symbol Directory](https://nasdaqtrader.com/Trader.aspx?id=symbollookup) | Listed-symbol discovery | Public download | No: page says current trading day | No | No | No | Current directory is insufficient | Daily event files exist | Using the current directory for 2018/2021/2022 would introduce survivor bias. Historical archive and redistribution terms were not validated. |
| Yahoo Finance Chart endpoint | Historical price experiment | No documented research contract verified | No | No | No | Provider-adjusted series observed | Incomplete in M11 stress set | Splits represented for many live symbols | Existing M11 curation resolved 11/13 observations, but SKLZ and VLDR were unresolved; the B0 request returned HTTP 429. It cannot be the only canonical dependency. |
| [Alpha Vantage](https://www.alphavantage.co/documentation/) | Independent adjusted-price candidate | Partial | Listing-status endpoint advertised; PIT completeness not validated | Vendor fundamentals available | Vendor dependent | Daily Adjusted includes split/dividend events | Not tested | Explicit split/dividend fields | API key normally required; standard free service is [25 requests/day](https://www.alphavantage.co/support/). The demo returned only the latest 100 rows, while full daily history and Daily Adjusted access are documented as premium constraints. Commercial/storage terms require review. |
| Stooq CSV endpoint | Independent price candidate | No-key endpoint attempted | No | No | No | Adjustment semantics not verified | Not verified | Not verified | The attempted CSV URL returned a JavaScript verification page rather than CSV. Official API and reuse terms were not established, so no data was accepted. |
| [OpenDART](https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DE003) | KR filings and XBRL | Yes with key | No | Yes | Filing dependent | No | Filings retained | Filing disclosures | Authentication key required; corporation-code and statement normalization are separate from market identity. |
| [KRX Data Marketplace](https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd?locale=en) | KR listing, prices, delisted screens | Public portal; bulk terms vary | Potentially | No | Listed-share fields appear in screens | Not proven in B0 | Delisted issue and price screens exist | Corporate-action evidence exists across screens | Stable documented bulk interface, historical identity continuity, adjustment semantics, and storage/license terms remain unresolved. |

“Free” above means no paid subscription was required for the tested public access. It is
not a grant of redistribution rights. No raw downloaded provider dataset or credential is
committed.

## Executed US source checks

The 2018, 2021, and 2022 SEC EFTS queries each returned HTTP 200, 100 filing hits, and a
reported total capped at 10,000. These 300 returned filing records are discovery results,
not 300 validated securities. They lack historical exchange membership, durable security
identity, and delisted continuity. Direct `master.idx` requests from this execution
environment separately returned HTTP 403 or timed out; the official archive itself is
documented and visible, so that access result is environment-specific rather than proof
that SEC data does not exist.

The Alpha Vantage IBM demo returned an adjusted series but only the latest 100 rows, not
the anchor periods. A Yahoo NVDA request returned HTTP 429. The Stooq NVDA request
returned HTTP 200 with a 796-byte browser-verification HTML page, not a price CSV. These
checks did not produce a legally reusable, independent two-source comparison for an
anchor-period security.

## Historical universe method attempted

The intended free construction was:

1. discover annual filers from SEC quarterly/full indexes;
2. remove funds and non-operating issuers using filing/security evidence;
3. crosswalk issuer CIK to a permanent security identity and exchange-membership interval;
4. preserve inactive/delisted securities;
5. only then run deterministic sampling.

Steps 1 and filing access are feasible. Step 3 was not solved with a free reproducible
source. The current Nasdaq directory cannot be used as the crosswalk. Consequently the
three `HistoricalUniverseSnapshot` values are unresolved and sampling correctly produces
no cohort.

## Sampling contract

The frozen pilot plan is not an investment rule:

- seed: `youngrich-m12-b0-free-first`
- version: `sha256-permanent-security-id-v1`
- maximum: 200 securities per anchor
- rank input: `version + seed + permanent_security_id`
- sampling occurs only after membership validation
- provider row order cannot affect selection
- duplicate identities fail validation
- unavailable selected companies are not replaced

The algorithm is executable and tested, but it was not applied to an invented or
survivor-only universe.

## Concrete paid-data gate

The observed blocker is a historical security master joining membership intervals,
permanent identities, corporate actions, delistings, and terminal outcomes. It is
required for an unbiased M12-B1; leaving all unavailable securities unresolved would
materially bias a broad run because missingness is related to failure/delisting.

Free remediation should be attempted first through an archived exchange/security-master
source with explicit storage rights. If that remains unavailable, the narrow paid
candidates are:

- [Norgate US Stocks Current & Past](https://norgatedata.com/data-content-tables.php),
  at a tier including delisted securities and historical constituents; or
- [CRSP US Stock Database](https://www.crsp.org/research/), specifically security/name
  history, exchange status, distributions, shares, and delisting returns.

No subscription is recommended or purchased by this pilot. Vendor licensing, coverage,
and integration cost require a separate decision.

## Research findings

- `HISTORICAL_US_SECURITY_MEMBERSHIP_FREE_SOURCE_GAP` — REQUIRES_VALIDATION.
- `DELISTED_PRICE_FREE_SOURCE_GAP` — OBSERVED in SKLZ/VLDR stress evidence.
- `SYSTEMATIC_QUANT_OUTCOME_DATASET_NOT_PRODUCED` — OBSERVED; no threshold or weight
  inference is allowed.

## Follow-up: M12-B0.1 Tiingo Free Price Pilot

The original FAIL result above remains unchanged. A separate
[Tiingo data pilot](tiingo-data-pilot-v0.1.md) now provides a thin, offline-tested
historical-price adapter and explicit split-versus-total-return normalization contract.
The 2026-09-05 credentialed run passed authentication and returned non-empty historical
EOD for 10 of 12 pilot symbols. Split and dividend semantics passed the bounded validation
set; VLDR and BBBY price coverage remained unresolved, and Search/metadata did not solve
terminal outcomes or historical identity. Its current status is
`LIVE PRICE PILOT PASS WITH GAPS`, not M12-B1 approval.

Even if the live price checks later pass, the point-in-time historical security master
and permanent-identity membership crosswalk remain unresolved. Tiingo may help the price
portion or a filing-anchored logic-calibration study; it cannot be assumed to make a
survivorship-safe full strategy backtest possible.
