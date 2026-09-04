# Market Data Plan

Status: RESEARCH

Authoritative: NO

Implementation Allowed: NO unless separately approved

Last Updated: 2026-09-04

## Questions to resolve

- Historical and production EOD provider selection
- Split-adjusted versus total-return-adjusted contracts
- Corporate-action and delisted-security coverage
- US-only versus US+KR identifiers, calendars, and currencies
- Licensing, redistribution, rate limits, corrections, and provenance
- Delayed versus realtime product requirement
- Benchmark history and versioned assignment policy

## Required provider capabilities

The selected source must expose durable instrument identity, timestamps, price basis,
adjustment/version metadata, corrections, and auditable provider references. Sparse or
unsafe series must resolve to unavailable rather than silently fall back to raw prices.

## Non-goals

No provider, API, schema migration, ingestion client, or product technology is selected
or authorized by this document.
