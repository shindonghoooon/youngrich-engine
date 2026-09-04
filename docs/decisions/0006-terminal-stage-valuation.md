# ADR-0006: Model Terminal Stage explicitly

Status: ACCEPTED

Date: 2026-09-04

## Context

An emerging company may still be in growth or transition at the valuation horizon.
Forcing mature economics can create false precision.

## Decision

Version terminal stage as `GROWTH`, `TRANSITION`, or `MATURE`, with rationale,
confidence, and conservative/base/premium exit evidence.

## Why

Stage uncertainty belongs in assumptions and confidence rather than hidden adjustments.

## Alternatives Considered

One mature terminal model; one fixed exit multiple.

## Consequences

Valuation can remain unresolved when terminal evidence is insufficient.

## Related Specs

[Common Valuation](../specs/valuation-v1.md)
