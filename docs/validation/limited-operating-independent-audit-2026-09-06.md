# Limited Operating Independent Audit Response

Status: VALIDATION — LOCAL PASS / REMOTE CI PENDING

Authoritative for Results: YES

Authoritative for Investment Rules: NO

Baseline: `82af10f1365bf313d211853f135d85fe5d05f29e`

Branch: `feat/limited-operating-flow`

Last Updated: 2026-09-06

This record reproduces the audit concerns against code. It does not copy the audit
verdict, change a frozen score, or represent a current investment recommendation.

## Reproduction classification

| Audit item | Baseline finding | Current result |
|---|---|---|
| Non-positive cumulative CFO in supporting CAPEX/CFO | Reproduced: the helper raised and stopped the Case 1 build | Fixed: CAPEX/CFO and its note are unresolved/not meaningful while signed CFO remains in Cash Economics |
| Annual continuity/comparability | Reproduced: Case 1 and Case 2 accepted nonconsecutive or short-gap annual observations | Fixed: consecutive fiscal labels and 330–400 day annual gaps are required |
| Valuation evidence publication timing | Reproduced: the common builders did not validate evidence availability or each exit-multiple timestamp | Fixed: both evidence layers must be public by valuation `as_of` |
| Required Quant metric identity | Additional evidence was required: builders emitted the expected metrics, while Case 1 lacked an explicit post-build Core contract | Fixed: actual Case 1 Core 8 and Case 2 Core 6 outputs are checked at their policy boundaries; supporting relabeling cannot bypass the check |
| Actual valuation-input fingerprint | Reproduced: common builders left the fingerprint absent and the limited pilot initially used a fixture-file hash | Fixed: versioned deterministic hashes use actual EPS or revenue/share inputs and exclude price, execution time, and random IDs |
| UNKNOWN flag transitions | Reproduced: absent flag membership could be read as false | Fixed: YES/NO/UNKNOWN is preserved; UNKNOWN→YES is resolution, not NO→YES |
| Policy-only change | Already fixed in the limited evaluation comparison; not represented by the general snapshot diff | Fixed in both paths as `POLICY_CHANGE` |
| Instrument/currency/unit/accounting/share basis | Partially fixed: ticker, currency, RAW price, and share-basis guard existed; unit/scope were not part of the evaluation comparison contract | Fixed in limited evaluation schema v0.2; missing historical scope remains unresolved |
| Ambiguous/unimplemented Router entry | Reproduced: the fallback promoted ambiguity to Quality Compounder | Fixed: ambiguity returns unresolved and executable entry blocks unimplemented Cases |
| Offline branch/PR CI | Reproduced: no workflow existed | Fixed in branch with token-free full pytest, documentation, and diff checks |

## Regression evidence

Local results after the audit response:

- Full suite: 428 passed
- Independent audit regressions: 31 passed
- Documentation consistency: included in the full suite
- Case 2 Golden validation: unchanged and passing
- Frozen policy specification tests: unchanged and passing
- DB migration: unchanged

The actual builder → SQLite store → new-session restore → snapshot comparison matrix covers:

- price only → `PRICE_ONLY`
- revenue only → `FUNDAMENTAL_CHANGE`
- shares only at the same price → `FUNDAMENTAL_CHANGE`
- price plus revenue → `MIXED`
- assumptions only → `ASSUMPTION_CHANGE`
- Investment Grade policy only → `POLICY_CHANGE`
- either historical fingerprint missing → `UNRESOLVED`

Case 1 EPS changes also change the generated fingerprint, while price-only changes do not.
The approved Case 2 shareholder-comparability provisional exception remains unchanged.

## Boundaries and unresolved items

- No Tiingo credential was present during local validation. STRL, TEM, and LPTH live
  execution remains `PENDING_CREDENTIAL` for session 2026-09-04.
- Remote CI and repository branch-protection status must be checked after push.
- M12-B1 remains BLOCKED. This work does not solve historical universe membership,
  delisted continuity, terminal payoff, or production data licensing.
- Historical records without fingerprints or v0.2 input-scope fields remain readable,
  but comparisons are unresolved rather than guessed.
- Existing relational Current Trend boolean columns remain active-flag projections for
  migration compatibility. Tri-state YES/NO/UNKNOWN in the immutable payload/domain model
  is authoritative; consumers must not interpret a false projection as proven NO.
