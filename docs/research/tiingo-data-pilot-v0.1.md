# Tiingo Data Pilot v0.1

Status: RESEARCH — LIVE PRICE PILOT PASS WITH GAPS

Authoritative: NO

Implementation Allowed: NO unless separately approved

Last Updated: 2026-09-05

## Purpose and boundary

M12-B0.1 evaluates Tiingo Starter as a possible historical-price source and a
research-only identity aid. It does not select a production provider, repair the missing
point-in-time security master, authorize M12-B1, or change frozen Case 1/2 and
calibration behavior.

The provider adapter is intentionally thin. It authenticates, parses metadata, Search,
and EOD responses, retains provenance, handles provider errors and caching, and converts
validated provider observations into the existing price contracts. It does not calculate
Case metrics or invoke calibration logic.

## Credential and executed status

- Credential environment variable: `TIINGO_API_TOKEN`
- Authentication transport: `Authorization: Token <token>` HTTP header
- Token detected in the execution environment: **YES**
- Live authentication, AAPL metadata, and AAPL EOD smoke test: **PASS**
- Live pilot symbols requested: **12**
- Non-empty historical EOD series: **10**
- Unresolved/no-price symbols: **2** (`VLDR`, `BBBY`)

The token value must never appear in source, fixtures, tests, documentation, cache keys,
URLs, logs, or Git history. Normal pytest runs are offline. A missing token stops the
manual command before any network request.

## Starter plan, limits, and license boundary

The [Tiingo pricing page](https://www.tiingo.com/pricing) described the free Starter plan
at review time as 500 unique symbols per month, 50 requests per hour, 1,000 requests per
day, 1 GB per month, and 30+ years of history. These are provider limits and may change;
the provider page is authoritative.

Tiingo data is treated as internal research data only. Raw responses are not committed or
redistributed. Production use, long-term storage, publication, and redistribution require
a separate license review. A successful technical pilot would not itself grant those
rights.

## Endpoints and fields

The manual client follows the official documentation:

- authentication: `/api/test/`
- EOD metadata: `/tiingo/daily/{ticker}`
- historical EOD: `/tiingo/daily/{ticker}/prices`
- research-only Search beta: `/tiingo/utilities/search/{query}`

Every parsed EOD observation preserves raw `open`, `high`, `low`, `close`, and `volume`;
adjusted `adjOpen`, `adjHigh`, `adjLow`, `adjClose`, and `adjVolume`; and `divCash` and
`splitFactor`. Series provenance retains provider, retrieval time, requested ticker and
date range, and metadata identity.

Metadata preserves ticker, name, exchange code, and available start/end dates. Search
preserves `isActive`, `permaTicker`, and `openFIGI` when supplied. Search remains a beta,
research-only aid and cannot silently become the canonical security master.

## Price-basis normalization contract

Tiingo documentation describes adjusted prices as split- and dividend-adjusted. The
youngrich-engine contract remains more explicit:

- `RAW` preserves raw close, but the existing Performance Engine does not accept it for
  adjustment-safe performance.
- `SPLIT_ADJUSTED` is derived from raw close and `splitFactor`; it is exposed only after a
  corporate-action validation confirms the mechanical raw-price ratio, adjusted-price
  continuity, and reported split factor.
- `TOTAL_RETURN_ADJUSTED` may use Tiingo `adjClose` only after both split and dividend
  evidence validate the expected economic-return convention.

The dividend check compares the raw economic return `(close + divCash) / previous close
- 1` with the `adjClose` return around the event. This keeps provider terminology out of
the engine's existing price-basis definitions.

Live validation passed for four split examples: AAPL 4:1, NVDA 4:1, TSLA 5:1 and 3:1,
and SKLZ 1:20 reverse split. The independently normalized raw return and Tiingo adjusted
return agreed within floating-point precision. The test compares those two returns
directly, so an ordinary same-day market move is not mislabeled as an adjustment error.

Dividend validation passed across 24 events each for AAPL, NVDA, SPY, and VTI. The
largest absolute difference between the raw cash-inclusive return and `adjClose` return
was below `2e-11`. For this tested request version, both the raw-plus-split-factor
`SPLIT_ADJUSTED` basis and provider `adjClose` `TOTAL_RETURN_ADJUSTED` basis are approved
for further research use. This is not approval of Tiingo as the production canonical
provider or evidence about untested securities.

## Executed live pilot

The bounded pilot list is:

- normal/growth: AAPL, ADBE, CRWD
- split/action: NVDA, TSLA
- reverse-split/failure: SKLZ
- failed/delisted or acquired exploration: VLDR, FSLY, TWTR, BBBY
- benchmarks: SPY, VTI

The 2018-01-01 through 2023-12-31 request produced:

| Symbol | Observations | First / last observation | Result |
|---|---:|---|---|
| AAPL | 1,509 | 2018-01-02 / 2023-12-29 | resolved |
| ADBE | 1,509 | 2018-01-02 / 2023-12-29 | resolved |
| CRWD | 1,147 | 2019-06-12 / 2023-12-29 | resolved from listing start |
| NVDA | 1,509 | 2018-01-02 / 2023-12-29 | resolved |
| TSLA | 1,509 | 2018-01-02 / 2023-12-29 | resolved |
| SKLZ | 927 | 2020-04-27 / 2023-12-29 | resolved from listing start |
| VLDR | 0 | none | metadata and EOD HTTP 404 |
| FSLY | 1,164 | 2019-05-17 / 2023-12-29 | resolved from listing start |
| TWTR | 1,216 | 2018-01-02 / 2022-10-28 | resolved through metadata end date |
| BBBY | 0 | none | partial metadata; EOD returned no observations |
| SPY | 1,509 | 2018-01-02 / 2023-12-29 | resolved |
| VTI | 1,509 | 2018-01-02 / 2023-12-29 | resolved |

Metadata and actual coverage agreed for ordinary/listing-start cases. TWTR demonstrates
that historical prices may end with a corporate event, but neither the last price nor
metadata `endDate` provides a terminal payoff. VLDR remained unavailable under its old
ticker. BBBY Search exposed both a current/reused ticker identity and the older BBBYQ
identity, while EOD for BBBY was empty. These results reinforce rather than solve the
historical-identity and terminal-outcome problem.

Search returned `permaTicker` and sometimes `openFIGIComposite`, but several results were
ambiguous: exact TWTR and VLDR stock records were absent, and Search marked identities as
active in ways that cannot establish historical listing status. Search remains a beta
supporting lookup, not a point-in-time security master.

## Rate and cache behavior

The client avoids duplicate requests through a deterministic cache key based on endpoint,
non-secret parameters, and request version. It handles HTTP 429 as a structured error,
honors `Retry-After` when present, and has configurable bounded retry/backoff behavior.
The pilot is deliberately sequential rather than parallel. No HTTP 429 was observed in
the live run. Structured 429 and bounded `Retry-After` behavior remain covered offline.

Raw response caches and the internal pilot summary live under `data/local/tiingo/`, which
is covered by the repository's existing `data/local/` ignore rule. Git may contain only
code, request contracts, checksums or summaries that do not redistribute provider data,
and synthetic test responses. The second pilot pass reused cached successful metadata,
EOD, and Search responses. HTTP failures are not treated as successful cache entries.

## Existing Performance Engine integration

After price-basis validation, the manual pilot maps a validated split-adjusted series to
existing `PriceSnapshot` records and calls the current Performance Engine. It does not
reimplement 6M/1Y return or MDD formulas. Five matching existing stress samples—ADBE
FY2017/FY2021, NVDA FY2018, CRWD FY2020, and FSLY FY2021—resolved 6M return, 1Y return,
and sufficient MDD coverage. TSLA FY2014 was correctly unresolved because the bounded
provider request began in 2018; the pilot did not expand its approved range.

Tiingo EOD `date` is treated as a trading-session label, not an executable or publication
timestamp. The research mapper converts US observations to scheduled 16:00
`America/New_York` regular close with daylight-saving handling. Early-close and full
exchange-calendar normalization remain future data-layer work.

## Current verdict and unresolved limitations

**LIVE PRICE PILOT PASS WITH GAPS.** Tiingo supplied coherent long-window EOD history for
10 of 12 selected symbols, and the tested split/dividend semantics support explicit
split-adjusted and total-return-adjusted research mappings. It did not provide usable EOD
for VLDR or BBBY and did not establish terminal payoff, identity continuity,
survivorship-safe membership, production licensing, or M12-B1 readiness.

Even a successful price pilot would address only part of the original M12-B0 failure.
The point-in-time historical security universe and permanent-security membership
crosswalk remain separate blockers. Tiingo price success could support a future
filing-anchored logic-calibration pilot without proving that a survivorship-safe full
strategy backtest is possible.

The live result can support review of a separately approved, small filing-anchored
logic-calibration pilot. It does not authorize the 200-symbol run or a survivorship-safe
full strategy backtest.
