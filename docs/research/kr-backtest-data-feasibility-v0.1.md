# KR Backtest Data Feasibility v0.1

Status: RESEARCH

Authoritative: NO

Implementation Allowed: NO unless separately approved

Last Updated: 2026-09-04

## Scope

This is a small market-adapter feasibility spike, not a Korean cohort backtest. The target
contract is unchanged:

`DART / KRX / KR price source → KR normalization → existing Case adapter → Generic Calibration Kernel`

No DART/KRX production client, statistics, investment-rule change, or database migration
is included.

## Source feasibility

| Need | Candidate | Feasibility | Remaining gap |
|---|---|---|---|
| Point-in-time reports | [OpenDART disclosure and financial APIs](https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DE003) | Strong: official report identifiers and XBRL statement endpoints exist | API key, amendment selection, GAAP/IFRS scope, and issuer-code versioning must be implemented and tested. |
| Company identity | OpenDART corporation-code endpoint | Moderate | Corporation code is not a permanent listed-security identity; share classes and listing intervals need KRX linkage. |
| Listing/delisting | [KRX Data Marketplace](https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd?locale=en) | Promising: listed issues, delisted issues, and delisted-price screens are visible | Reproducible historical bulk export/API, stable identifiers, and storage rights were not established. |
| Actual shares | DART periodic reports plus KRX listed-share fields | Moderate | Treasury shares, multiple classes, rights/bonus issues, and comparable observation dates need explicit normalization. |
| Historical prices | KRX issue-price screens | Promising for raw exchange history | Split/rights/bonus-adjusted basis and a complete machine-readable series were not proven. |
| Corporate actions | DART filings plus KRX event/listing records | Conceptually available | A single action chain connecting predecessor/successor securities and executable payoff is not yet validated. |

OpenDART requires an authentication key and keeps that credential outside Git. KRX has
separate data products and usage policies; public screen access is not assumed to grant
bulk storage or redistribution.

## Tiny feasibility inventory

- Samyang Foods (`003230`) and LS ELECTRIC (`010120`) are normal listed-company evidence:
  existing official-source fixtures prove that KR annual financials can be normalized for
  Case 1. They are current validation fixtures, not historical B0 cohort observations.
- A Kakao-style stock-split event is the intended split/identity test.
- A Celltrion Healthcare-style merger/delisting is the intended predecessor/successor and
  terminal-payoff test.

The two corporate-action candidates are only proposed test identities. No event record,
adjusted price series, or payoff was accepted into a fixture in this spike. Therefore the
executed KR cohort N is zero and no performance claim is made.

## What is easy

- Official point-in-time disclosure discovery and filing provenance.
- Reuse of the existing Case 1/2 adapters after KR values are normalized.
- Preserving `period_end`, `available_at`, and `analysis_as_of` separately.
- Emitting explicit unresolved reasons through the common research-data contract.

## What is hard

- Historical security membership and share-class continuity across ticker/name changes.
- Actual-share comparability through rights, bonus, split, treasury-share, and merger events.
- Demonstrating that a historical price series is adjustment-safe for both returns and MDD.
- Delisting consideration and successor-security linkage.
- Automated bulk access and redistribution/storage terms for KRX data.

## Verdict

KR v1.1 is **conceptually feasible but execution-gated**. OpenDART plus KRX appears able
to cover the required roles, but B0 did not prove a reproducible free security master or
corporate-action-safe price pipeline. Treat this as `PASS_WITH_GAPS` for architectural
portability, not permission to run KR systematic statistics.
