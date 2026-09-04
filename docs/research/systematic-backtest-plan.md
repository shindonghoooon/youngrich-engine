# Systematic Historical Backtest Plan

Status: RESEARCH

Authoritative: NO

Implementation Allowed: NO unless separately approved

Last Updated: 2026-09-04

## Purpose

Design a future unbiased evaluation of frozen investment logic on a pre-defined,
point-in-time universe. This is separate from the curated, outcome-aware Historical
Stress Calibration.

## Required protocol

- Pre-declared universe and deterministic eligibility
- Explicit historical date range and snapshot cadence
- Point-in-time fundamentals, shares, market cap, and filing availability
- Historical routing using only then-public evidence
- Delisted-security inclusion and survivorship-bias control
- Corporate-action-safe price history
- Versioned benchmark assignments
- Leakage, completeness, and reproducibility tests

## Mandatory decision gate

Implementation cannot begin before explicit approval of Universe v1, Snapshot Cadence
v1, Data Source Plan v1, Benchmark Policy v1, and Historical Date Range v1. US-only
versus US+KR is part of the Universe/Data Source decision.

## Non-goals

This plan does not select providers, freeze a universe, optimize thresholds, change
investment rules, or authorize implementation.

See [M12 in the roadmap](../roadmap.md) and the [market-data plan](market-data-plan.md).
