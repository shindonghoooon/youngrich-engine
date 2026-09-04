# ADR-0001: Case-based analysis

Status: ACCEPTED

Date: 2026-09-04

## Context

Profitable growers, emerging loss-making businesses, cyclicals, mature quality, and
asset situations have different economic drivers. One formula would reward or penalize
the wrong behavior across these structures.

## Decision

Route the current investment idea to a Case before applying Case-specific Quant logic.

## Why

Case-specific economics preserve comparability without adding company exceptions.

## Alternatives Considered

One universal score; permanent company labels; ad hoc metric additions.

## Consequences

Router uncertainty remains explicit. New Cases require their own spec and validation.

## Related Specs

[Case 1](../specs/case1-v1.md), [Case 2](../specs/case2-quant-v1.md)
