# ADR-0010: Keep Performance downstream-only

Status: ACCEPTED

Date: 2026-09-04

## Context

Using subsequent returns to alter a historical analysis would leak future information
and invalidate calibration.

## Decision

Performance consumes immutable historical analysis and later adjustment-safe prices. It
cannot mutate Quant, Current, Narrative, Valuation assumptions, or Investment Grade.

## Why

This preserves the original decision and makes false-positive/false-negative diagnosis
honest.

## Alternatives Considered

Outcome-adjusted historical grades; in-place snapshot updates.

## Consequences

Rule changes occur only through separate versioned decisions based on repeated evidence.

## Related Specs

[Performance](../specs/performance-engine-v1.md), [Tracking Schema](../specs/tracking-schema-v1.md)
