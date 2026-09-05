# Limited Operating Flow — STRL / TEM / LPTH

Status: ACTIVE — DEMO/VALIDATION

Last Updated: 2026-09-06

This is a bounded operating connection, not a production feed or a current investment
recommendation. It connects existing fixtures and frozen engines without changing Case,
Valuation, or Investment Grade policy.

## Data flow

```text
existing validation analysis
  -> append-only SQLite analysis / assumptions
  -> exact completed-session Tiingo RAW close
  -> derived valuation and explicitly selected Investment Grade v1.1
  -> append-only local evaluation artifact
  -> structured comparison and CLI/JSON output
```

STRL demonstrates Case 1 Quant with missing valuation evidence, TEM demonstrates the full
Case 2 path, and LPTH demonstrates first-class `U` with structured reasons. The reference
TEM/LPTH analyses remain exact v1 Golden records. A new operating evaluation selects v1.1;
it does not rewrite those records.

## Run

Install the project with development dependencies. Then use an explicitly completed US
trading session:

```text
python -m research.limited_operating_flow run --session-date 2026-09-04
```

The command seeds STRL, TEM, and LPTH, requests only that exact session, stores a RAW close,
creates a derived v1.1 evaluation, and compares it with the previous compatible evaluation
when one exists. It never substitutes a nearby date. Use `--tickers TEM LPTH` to narrow the
bounded set.

Individual steps are also available:

```text
python -m research.limited_operating_flow seed
python -m research.limited_operating_flow refresh --ticker TEM --session-date 2026-09-04
python -m research.limited_operating_flow revalue --ticker TEM --price-snapshot-id <ID>
python -m research.limited_operating_flow show --ticker TEM
```

All commands emit structured JSON. `revalue`, `show`, and a successful `run` also emit a
short human-readable summary. Every export includes `usage_mode = DEMO/VALIDATION`, the
reference analysis, financial period and availability, original `as_of`, price session and
basis, assumption identity/version, policy version, unresolved reasons, and creation time.

## Local storage boundary

Defaults are ignored by Git:

- SQLite: `data/local/limited-operating/demo.sqlite3`
- derived evaluations: `data/local/limited-operating/evaluations.jsonl`
- Tiingo provider cache: `data/local/tiingo/`

SQLite stores Company/Instrument identity, immutable reference AnalysisSnapshots,
versioned Valuation assumptions, the original TEM/LPTH validation closes, and newly
imported RAW PriceSnapshots. The current persistence schema has no independent price-only
evaluation table. Derived Valuation/IG results therefore use the allowed append-only JSONL
artifact with source IDs and fingerprints. They are not inserted as fake new fundamental
AnalysisSnapshots. No migration is introduced.

Seed and price import are idempotent: an identical stable ID is reported as
`already_exists`; different content under the same ID fails.

## Price and evidence safety

- Valuation accepts only `PriceBasis.RAW` and the instrument currency.
- The price timestamp must map to the requested US market session.
- Case 2 market cap is explicitly estimated from RAW close and the fixture's latest
  officially reported actual shares. `reported_shares_as_of` remains visible.
- Unconfirmed split/share basis leaves valuation and IG unresolved.
- Financial, share, exit-evidence, and price timestamps cannot postdate `assessment_as_of`.
- Quant, Current, Narrative, and assumptions are loaded from the reference analysis and
  remain unchanged during repricing.
- A Funding Stress cap remains active after a lower price.
- A comparison is `PRICE_ONLY` only when reference analysis/fingerprint, complete
  assumption identity, and IG policy are unchanged. Policy changes are reported separately.

STRL has no approved company valuation/analyst assumption fixture. Its price and Quant can
be stored, but derived valuation remains absent and IG is `U` with
`VALUATION_UNRESOLVED` / `VALUATION_ASSUMPTIONS_UNAVAILABLE`. No assumption is invented.

## Credential and unavailable states

The live client reads only the `TIINGO_API_TOKEN` OS environment variable; `.env` is not
loaded automatically. The token value and Authorization header are never output. Without
the token, seed/offline tests still run and live refresh returns `PENDING_CREDENTIAL`.
An empty exact-session response returns `UNAVAILABLE` and does not mutate stored analysis.

Synthetic prices are used only by tests. Normal CLI operation never generates a fallback
price. Existing M12-B0 FAIL and M12-B1 BLOCKED status remain unchanged because this pilot
does not solve historical membership, delisted continuity, or terminal payoff.

## Verification

```text
python -m pytest tests -p no:cacheprovider
git diff --check
git diff --cached --check
```

Live calls do not belong in pytest. Re-run the bounded live command only when a credential
is available and record the exact tickers, session date, and observation count separately.
