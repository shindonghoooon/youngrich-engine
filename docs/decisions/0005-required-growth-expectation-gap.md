# ADR-0005: Use Required Growth and Expectation Gap

Status: ACCEPTED

Date: 2026-09-04

## Context

Growth-company valuation is often more informative as a question about what the current
price already requires than as a single asserted fair value.

## Decision

Calculate market-implied Required Growth under versioned scenarios and compare it with a
plausible growth range to derive Expectation Gap.

## Why

The method makes embedded expectations and uncertainty explicit.

## Alternatives Considered

One fixed target price; quality-only ranking; a single exit multiple.

## Consequences

Assumptions and confidence are versioned; price changes do not silently change them.

## Related Specs

[Common Valuation](../specs/valuation-v1.md)
