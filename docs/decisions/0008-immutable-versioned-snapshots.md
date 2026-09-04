# ADR-0008: Use immutable, versioned snapshots

Status: ACCEPTED

Date: 2026-09-04

## Context

Overwriting analysis destroys what was actually known and believed at a historical date.

## Decision

Append new Analysis, Thesis/KPI, Valuation, Grade, and Performance snapshots. Never
overwrite historical records when new financials or prices arrive.

## Why

Immutability enables no-look-ahead validation, diffs, attribution, and auditability.

## Alternatives Considered

Mutable current-state rows; implicit latest values without history.

## Consequences

Corrections and assumption changes require explicit versions and lineage.

## Related Specs

[Tracking Schema](../specs/tracking-schema-v1.md), [Persistence](../specs/persistence-v1.md)
