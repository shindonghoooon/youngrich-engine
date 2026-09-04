# ADR-0002: Separate Quant Quality from Investment Grade

Status: ACCEPTED

Date: 2026-09-04

## Context

A strong company can be a poor purchase at an excessive price, while an uncertain
company may retain valuable optionality.

## Decision

Quant measures Case-specific company quality. Valuation and explicit gates/caps produce
Investment Grade separately.

## Why

The separation prevents price or Narrative from rewriting accounting quality.

## Alternatives Considered

One blended company/stock score; Narrative-adjusted Quant.

## Consequences

Both grades must be displayed and interpreted independently.

## Related Specs

[Valuation](../specs/valuation-v1.md), [Investment Grade](../specs/investment-grade-v1.md)
