# Generic Stock Onboarding + Minimal Watchlist Registry v1

Status: FROZEN — input/service contract v1; implementation checkpoint

Version: 1.0

Authoritative: YES

Last Updated: 2026-09-06

Implementation: `engine/stock_onboarding.py`, `engine/watchlist_registry.py`, `engine/read_only_watchlist.py`, `engine/stored_analysis_view.py`, `research/stock_onboarding.py`, `research/watchlist.py`

Tests: `tests/test_stock_onboarding.py`, `tests/test_generic_watchlist.py`, `tests/test_persistence_migration.py`, `tests/test_read_only_watchlist.py`

Supersedes: fixed-ticker product enumeration only; legacy limited-operating replay remains.

Change Policy: explicitly version accepted-input and membership changes. No change to
frozen investment formulas, weights, thresholds or gates is authorized by this contract.

## Execution boundary

```text
Validated normalized artifact -> Company / Instrument -> existing Router
  -> Case adapter -> existing Quant / Current / Narrative / Valuation / IG v1.1
  -> immutable AnalysisSnapshot + input receipt -> optional ACTIVE membership
  -> local read-only projection
```

`StockOnboardingService.analyze(input, track=False)` has no ticker-specific branch,
fixture discovery, LLM, network or scheduler. Company and tradable Instrument have
distinct stable IDs; ticker is not a global identity. Case 1/2 are supported; uncertain
routing returns `CASE_UNRESOLVED`, other Cases `BLOCKED_UNIMPLEMENTED_CASE`. Neither
creates a fictitious analysis/U. Membership may still be ACTIVE with no analysis.
The future Agent orchestrates services, never formulas, grades or invented assumptions.

## Normalized input v1

`OnboardingInput` is frozen, extra-fields-forbidden, JSON serializable and revalidated
at service entry, including model-copy inputs. It requires a request ID, Company,
Instrument, Router facts, aware as_of/created_at, source/publication provenance,
currency/financial scale, reported GAAP scope and explicit usage classification.

- Case 1 uses `Case1BacktestInput` / normalized `FinancialHistory` in base currency
  units through the existing adapter/Case 1 builder. Optional canonical Current input
  must use `case1-current-v1-frozen`; no new Current formula is added.
- Case 2 uses `Case2QuantInput` and optional `Case2CurrentInput` through existing
  component builders. Monetary totals share the declared scale (1/1,000/1,000,000);
  common-share counts are actual individual shares. Valuation market cap is RAW close
  times actual shares divided by financial scale. Annual continuity/330–400-day
  comparability remains the existing input contract.
- Narrative contains explicit versioned analyst states; the existing Case 2 Gate is
  reused. No new business evidence or KPI observation is generated.
- Optional Valuation inputs contain unchanged assumption ID/version, usage and approval
  reference, required return, existing evidence/asymmetry, actual shares and their
  period/publication date, and an explicit verified RAW-price/share/EPS split-basis
  assertion. Unconfirmed basis leaves valuation unresolved.
- Validation-only assumptions remain `DEMO/VALIDATION`, never automatically promoted
  to `APPROVED`. Approval reference is supplied provenance, not program-inferred approval.
- `period_end`, financial `available_at`, `as_of`, and `price_session_date` stay separate.
  Late `retrieved_at` does not turn already-public evidence into look-ahead.

Optional price must identify the same Instrument/company/currency and be RAW close.
Its aware timestamp must map to the supplied exchange timezone/session and must not
postdate as_of or precede required public information. No nearby-session substitution,
adjusted-price/raw-EPS mixing or synthetic fallback. Acquisition is responsible for
establishing an actual executable session; this service checks supplied contracts.

Missing assumptions: `VALUATION_ASSUMPTIONS_UNAVAILABLE`; missing price:
`PRICE_UNAVAILABLE`; unconfirmed split basis: `SHARE_SPLIT_BASIS_UNRESOLVED`.
Analysis can succeed with unresolved Valuation and IG U, and U can be tracked.
IG v1.1 accepts absent Valuation without fabricating an assumption set. Its existing
mandatory-evidence gates and valid terminal-breaker X precedence are unchanged.
Historical v1 replay remains untouched.

## Persistence and replay

Additive revision `20260906_0003` adds `watchlist_memberships` and `onboarding_records`.
Existing historical schemas/data are not rebuilt. Receipts preserve normalized input,
its SHA-256 fingerprint and structured result. This request fingerprint includes full
input provenance; it is distinct from the existing price-independent valuation
fundamental fingerprint, whose contract is unchanged.

Analysis IDs derive from request ID, not ticker/wall clock. Same request/input reuses
history; changed input with the same ID fails. A new request appends a new snapshot.
Identity, price and assumption-version collisions must compare equal or fail, never
overwrite. An outer transaction contains existing repositories' individual commits:
failed onboarding does not leave partial identity/history/receipt writes. Replay with
`track=True` can register an existing analysis without recalculation.

Optional tracking refs must resolve to an existing scoped Thesis version and its KPI
definitions. No automatic definitions/observations. Without an explicit registered ref,
status is `NOT_REGISTERED`, even if validation Narrative mentions KPI IDs.

## Membership and read model

One membership per instrument (database UNIQUE), with company/instrument IDs,
ACTIVE/INACTIVE status, activation/deactivation dates, nullable reference analysis,
created_at and registration source. Re-adding ACTIVE is a no-op including its original
reference. Reactivation keeps membership ID/created_at, starts a new active interval,
clears stopped_at and optionally takes an explicit new reference. This v1 row is current
lifecycle state, not an interval ledger. Deactivation deletes no analysis, price,
evaluation, Diff, Performance or Thesis/KPI history.

`list_active_watchlist()` returns ACTIVE membership, stable Instrument, reference and
latest analysis. The future Daily Tracker consumes this API, not a ticker tuple.
UI reads SQLite using mode=ro/query_only and optionally legacy JSONL. Initial analysis
is labeled initial, not a fabricated price update. Legacy v1/v1.1 labels remain.
Missing analysis/price evaluation is a data state, not a calculated U; a saved U keeps
its saved reasons. Instrument-qualified selection handles ticker collisions/renames.
Grades, decision trace, usage/provenance, price date and business periods remain visible.
Reload only rereads stored records; no analysis/revalue/migration/registration/network.

## Explicit local CLI

Use absolute local paths. No Tiingo credential is required.

```text
python -m research.watchlist migrate --db <local.sqlite>
python -m research.stock_onboarding analyze --input <normalized.json> --db <local.sqlite>
python -m research.stock_onboarding analyze --input <normalized.json> --db <local.sqlite> --track
python -m research.watchlist add --db <local.sqlite> --instrument-id <stable-id>
python -m research.watchlist list --db <local.sqlite>
python -m research.watchlist deactivate --db <local.sqlite> --instrument-id <stable-id>
python -m streamlit run app/read_only_watchlist.py --server.address 127.0.0.1 -- --db <local.sqlite>
```

Migration is explicit, never view-triggered. A complete unstamped legacy v0002
create_all DB is structurally checked, stamped and additively upgraded; partial or
unknown schemas require review. Back up valuable local files first. No auto-registration.
The explicit bootstrap below uses existing identity and registers membership only:

```text
python -m research.watchlist register-existing-watchlist --db <existing.sqlite> --instrument-id <existing-id> --instrument-id <another-id>
python -m streamlit run app/read_only_watchlist.py --server.address 127.0.0.1 -- --db <existing.sqlite> --artifacts <corresponding-existing.jsonl>
```

New generic analyses need no dummy JSONL. Keep local DB/JSONL and private input artifacts
in ignored local storage, not Git. IONQ proof converts the existing Golden fixture only
in a test adapter; product code never reads `tests/fixtures/<ticker>.json`.

## Next, separately approved

Daily EOD Tracking -> Stock Agent -> Fundamental/Event -> Tracking KPI Automation ->
Daily Brief/Alerts. Daily repricing must preserve financial/assumption versions and the
PRICE_ONLY / FUNDAMENTAL_CHANGE / ASSUMPTION_CHANGE / POLICY_CHANGE / MIXED / UNRESOLVED
comparison contract. None is implemented here. Case 3–6 and M12-B1 research are separate;
M12-B1 remains BLOCKED.
