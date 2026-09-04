# ADR-0004: Do not calculate a weighted Investment Grade

Status: ACCEPTED

Date: 2026-09-04

## Context

A weighted average can let strong growth numerically cancel a thesis breaker, funding
stress, or unacceptable valuation.

## Decision

Use valuation as the initial grade and apply ordered, auditable gates and caps.

## Why

Non-compensatory risks should remain visible and enforceable.

## Alternatives Considered

Weighted layer average; opaque discretionary final score.

## Consequences

Every grade adjustment carries an explicit trigger, maximum, and rationale.

## Related Specs

[Investment Grade](../specs/investment-grade-v1.md)
