# Developer Handoff

Last Updated: 2026-09-05

Status: INTEGRATION CHECKPOINT

This file is a short execution handoff. Frozen specifications and executable tests remain
authoritative; validation fixtures are not current investment recommendations.

## Repository State

- Repository: `D:\youngrich-engine\youngrich-engine`
- B0/Tiingo branch: `main`
- B0/Tiingo checkpoint: `858ca72176c013113b1e0c9d37d46dee6f8b2fbc`
- Safety worktree: `D:\youngrich-engine\youngrich-engine-decision-safety-v1_1`
- Safety branch: `fix/decision-safety-v1_1`
- Safety checkpoint: `db634119522ff8e4e347f03f4013b30ff0de9982`
- Integration worktree: `D:\youngrich-engine\youngrich-engine-integration-safety-tiingo-v1_1`
- Integration branch: `integration/safety-tiingo-v1_1`

Do not delete either source worktree as part of this checkpoint. Determine the final
commit with `git rev-parse HEAD`; this document intentionally does not predict its own
commit hash.

## Decision Safety v1.1

Read:

- `docs/specs/investment-grade-v1.md` for exact historical replay
- `docs/specs/investment-grade-v1.1.md` for new decision-safety behavior
- `docs/decisions/0012-investment-grade-decision-safety-v1-1.md`
- `docs/validation/decision-safety-v1.1.md`

`Case2AnalysisInput.investment_grade_policy_version` in `engine/case2_analysis.py`
defaults to `InvestmentGradePolicyVersion.V1` so existing Golden results replay without
rewriting history. New operating evaluations must explicitly select
`InvestmentGradePolicyVersion.V1_1`. The resulting Investment Grade snapshot records
`investment-grade-v1.1-safety` and structured reasons. `Case2QuantBacktestAdapter` in
`engine/case_backtest_adapters.py` is the Quant-only path; it does not fabricate Current,
Narrative, Valuation, or Investment Grade inputs.

The five-company comparison is fixture-, `as_of`-, and assumption-specific. LPTH `U`
means the decision evidence is unresolved, not that the company was judged worse. The
reproduced v1 issue is missing mandatory Quant/Narrative evidence and the unsupported
LOW-confidence path; `NEGATIVE / UNFAVORABLE` remains `D` at both HIGH and LOW confidence.

## Tiingo Research Price Path

Read:

- `docs/research/tiingo-data-pilot-v0.1.md`
- `docs/validation/m12-b0.1-tiingo-data-pilot-v0.1.md`
- `docs/validation/m12-b0-free-data-pilot-v0.1.md`

Authentication is read only from the `TIINGO_API_TOKEN` operating-system environment
variable. The token is not present in the current integration shell. Its value must never
be printed or committed. The code does not automatically load `.env` files.

Provider responses and pilot summaries are cached under ignored
`data/local/tiingo/`; do not stage or copy this directory. The completed live validation
received non-empty EOD data for 10 of 12 requested symbols. VLDR and BBBY remained
unresolved, and TWTR's last observed price is not terminal-payoff evidence.
`SPLIT_ADJUSTED` and `TOTAL_RETURN_ADJUSTED` are approved only for the documented research
scope. Historical security membership, delisted continuity, terminal payoff, production
licensing, and production-provider approval remain unresolved. M12-B0 therefore remains a
FAIL entry gate and M12-B1 systematic execution remains BLOCKED.

Do not rerun the 12-symbol live pilot unless authentication, response parsing, or price
adjustment behavior changes. Offline tests are the normal regression path.

## Verified Commands

Use a Python environment installed with `.[dev]`, then run:

```text
python -m pytest tests -p no:cacheprovider
python -m pytest tests/test_case2_golden_validation.py tests/test_decision_safety_v1_1.py
python -m pytest tests/test_research_data_pilot.py tests/test_tiingo_research_source.py
python -m pytest tests/test_documentation_consistency.py
git diff --check
git diff --cached --check
```

The source worktrees passed 363 B0/Tiingo tests and 355 safety tests before integration.
The integrated worktree passed the following checks on 2026-09-05:

- Integrated full suite: 379 passed
- Focused cross-layer regression: 135 passed
- Documentation consistency: 7 passed (also included in both runs above)
- Unstaged and staged diff checks: PASS
- Secret literal and local raw-cache staging checks: PASS

## Next Product Task

Build one limited operating vertical slice for STRL, TEM, and LPTH:

```text
existing official fixture / analysis
  -> existing append-only DB persistence
  -> Tiingo RAW close for an explicitly completed trading day
  -> valuation and Investment Grade v1.1 using the existing versioned assumptions
  -> structured comparison with the prior result
```

STRL covers Case 1, TEM covers Case 2, and LPTH proves that `U` and its missing evidence
remain visible. Validation-only assumptions and fixtures must be labeled
`DEMO/VALIDATION`, never presented as current approved investment grades. Do not overwrite
an old `AnalysisSnapshot`; price-only changes create a separate derived
valuation/evaluation while preserving the assumption version. Valuation uses the RAW price
with matching share/EPS scope, while performance uses a consistent adjusted price basis and
version.

Start with the smallest executable connection among existing functions. A minimal mobile
query view comes only after this path works. Do not add realtime prices, broker integration,
a new provider, a full historical universe, automatic threshold changes, a new Case, or a
large systematic backtest in the next task.
