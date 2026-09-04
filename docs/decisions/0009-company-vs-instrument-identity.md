# ADR-0009: Separate Company from Instrument identity

Status: ACCEPTED

Date: 2026-09-04

## Context

Tickers can change, collide across exchanges, or represent multiple listings of the same
business.

## Decision

Use Company as durable business identity and Instrument as the tradable listing. Ticker
is an attribute, not the global key.

## Why

This supports listing changes, currencies, exchanges, and benchmark assignments without
rewriting company history.

## Alternatives Considered

Ticker-only identity; company and listing in one table.

## Consequences

Persistence and price records require explicit instrument resolution.

## Related Specs

[Persistence](../specs/persistence-v1.md), [Tracking Schema](../specs/tracking-schema-v1.md)
