# ADR-0007: Treat Price as first-class data

Status: ACCEPTED

Date: 2026-09-04

## Context

Company quality does not determine purchase attractiveness without a market price, and
historical evaluation requires an exact reference price.

## Decision

Store versioned `PriceSnapshot` records used by Valuation, Expectation Gap, Investment
Grade, Entry Zone, and Performance.

## Why

Explicit prices make repricing, timing, provenance, and performance reproducible.

## Alternatives Considered

Embedding price in reports; implicit latest price; technical-indicator layer.

## Consequences

Price-only updates create new outputs while preserving assumptions. Technical indicators
remain outside v1.

## Related Specs

[Tracking](../specs/tracking-engine-v1.md), [Performance](../specs/performance-engine-v1.md)
